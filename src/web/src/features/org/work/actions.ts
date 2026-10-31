"use server";

import { revalidatePath } from "next/cache";

import { actionError, type ActionState } from "@/features/pathway/action-state";
import { getApi } from "@/lib/api";

const REASONS = ["already_have_skill", "pace", "language", "accessibility", "schedule", "upfront_cost", "target_role", "other"] as const;
type Reason = (typeof REASONS)[number];

function text(form: FormData, key: string, max = 120): string {
  const value = form.get(key);
  return typeof value === "string" ? value.slice(0, max) : "";
}

async function settle(request: Promise<{ error?: unknown; response: Response }>): Promise<ActionState> {
  try {
    const { error, response } = await request;
    if (error !== undefined || !response.ok) return { error: actionError(error, response.status) };
  } catch {
    return { error: "Your change couldn’t be saved. Please try again." };
  }
  revalidatePath("/work", "layout");
  revalidatePath("/org", "layout");
  return { done: Date.now() };
}

/** The member accepts, declines (optional programmes only) or asks to change an agreement. */
export async function decideProgrammeAction(_: ActionState, form: FormData): Promise<ActionState> {
  const raw = text(form, "decision");
  const decision = raw === "accept" || raw === "decline" ? raw : "request_change";
  const reasonRaw = text(form, "reason");
  const reason = REASONS.find((r) => r === reasonRaw) as Reason | undefined;
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  return settle(
    api.POST("/api/v1/org/programmes/{programme_id}/decision", {
      params: {
        path: { programme_id: text(form, "programme_id", 80) },
        query: org_id ? { expected_org: org_id } : undefined,
      },
      body: {
        decision,
        reason: decision === "request_change" ? (reason ?? null) : null,
        note: text(form, "note", 500),
        proposed_role_id: decision === "request_change" ? text(form, "proposed_role_id", 80) || null : null,
        // Only an explicit tick counts; members who already share skills need none.
        consent: decision === "accept" && form.get("consent") === "on",
      },
    }),
  );
}

export async function proposePackageRoleAction(_: ActionState, form: FormData): Promise<ActionState> {
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  return settle(api.POST("/api/v1/org/packages/assigned/propose-role", {
    params: org_id ? { query: { expected_org: org_id } } : undefined,
    body: { token: text(form, "token", 64), proposed_role_id: text(form, "proposed_role_id", 80) },
  }));
}

/** The member turns skill-level sharing with this organisation on or off. */
export async function setSharingAction(_: ActionState, form: FormData): Promise<ActionState> {
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  return settle(
    api.PUT("/api/v1/org/me/sharing", {
      params: org_id ? { query: { expected_org: org_id } } : undefined,
      body: { share_skills: text(form, "share") === "on" },
    }),
  );
}
