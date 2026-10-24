"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { call, getApi } from "@/lib/api";
import { clearSession, setSessionToken } from "@/lib/auth/session";
import { safeReturn } from "@/lib/navigation";

export type AuthState = { error?: string; values?: Record<string, string> };

function text(form: FormData, key: string, max = 254): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

/** Keep what the person typed (never the password) so an error does not wipe the form. */
function keep(form: FormData): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of form.entries()) {
    if (key !== "password" && !key.startsWith("$") && typeof value === "string") out[key] = value;
  }
  return out;
}

function destination(next: string, apiNext: string): string {
  // Keep valid personal/employee deep links. Workspace layouts check the membership/role.
  if (!next) return apiNext;
  const mode = apiNext.startsWith("/org") ? "organisation" : "individual";
  const safe = safeReturn(next, mode);
  // New learners must finish intake first.
  return apiNext === "/app/onboarding" ? apiNext : safe;
}

export async function signupAction(_: AuthState, form: FormData): Promise<AuthState> {
  const workspace = text(form, "workspace") === "organisation" ? "organisation" : "individual";
  const size = Number.parseInt(text(form, "size", 7), 10);
  const joinCode = workspace === "individual" ? text(form, "join_code", 16) || null : null;
  const shareSkills = workspace === "individual" && Boolean(joinCode) && form.get("share_skills") === "on";
  if (joinCode && !shareSkills) {
    return {
      error: "Consent to share your skill profile with the organisation is required when signing up with a join code.",
      values: keep(form),
    };
  }
  const api = await getApi();
  const result = await call(
    api.POST("/api/v1/auth/signup", {
      body: {
        display_name: text(form, "display_name", 80),
        email: text(form, "email"),
        password: typeof form.get("password") === "string" ? String(form.get("password")).slice(0, 128) : "",
        workspace,
        consent: form.get("consent") === "on",
        join_code: joinCode,
        share_skills: shareSkills,
        organisation:
          workspace === "organisation"
            ? {
                type: text(form, "org_type") === "institution" ? "institution" : "company",
                name: text(form, "org_name", 120),
                industry: text(form, "industry", 120),
                size: Number.isFinite(size) && size >= 0 ? size : 0,
              }
            : null,
      },
    }),
  );
  if (!result.ok) return { error: result.message, values: keep(form) };
  await setSessionToken(result.data.token);
  redirect(destination(text(form, "next", 300), result.data.next_path));
}

export async function loginAction(_: AuthState, form: FormData): Promise<AuthState> {
  const api = await getApi();
  const result = await call(
    api.POST("/api/v1/auth/login", {
      body: {
        email: text(form, "email"),
        password: typeof form.get("password") === "string" ? String(form.get("password")).slice(0, 128) : "",
      },
    }),
  );
  if (!result.ok) return { error: result.message, values: keep(form) };
  await setSessionToken(result.data.token);
  redirect(destination(text(form, "next", 300), result.data.next_path));
}

export async function joinOrgAction(_: AuthState, form: FormData): Promise<AuthState> {
  const consent = form.get("consent") === "on";
  if (!consent) {
    return { error: "Please consent to join the organisation and share your profile.", values: keep(form) };
  }
  const api = await getApi();
  const result = await call(
    api.POST("/api/v1/org/join", {
      body: { code: text(form, "code", 16), share_skills: true, consent: true },
    }),
  );
  if (!result.ok) return { error: result.message, values: keep(form) };
  revalidatePath("/app", "layout");
  return { values: { joined: result.data.name, org_id: result.data.id } };
}

export async function signOutAction(): Promise<void> {
  await clearSession();
  redirect("/");
}

/** Permanently delete the signed-in account after the API re-checks the password. */
export async function deleteAccountAction(_: AuthState, form: FormData): Promise<AuthState> {
  const password = typeof form.get("password") === "string" ? String(form.get("password")).slice(0, 128) : "";
  if (form.get("confirm") !== "on") return { error: "Tick the box to confirm." };
  const api = await getApi();
  const result = await call(api.POST("/api/v1/auth/me/delete", { body: { password } }));
  if (!result.ok) return { error: result.message };
  await clearSession();
  redirect("/?deleted=1");
}
