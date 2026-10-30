"use server";

import { revalidatePath } from "next/cache";
import { call, getApi } from "@/lib/api";
import type { ActionState } from "@/features/pathway/action-state";

const text = (f: FormData, key: string) => String(f.get(key) ?? "").trim();

/** HR sets a member's yearly training budget (used to build the budget-capped package). */
export async function budgetAction(_: ActionState, form: FormData): Promise<ActionState> {
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  const year = Number(text(form, "year"));
  const result = await call(api.PUT("/api/v1/org/funding/{year}/budget", {
    params: { path: { year }, query: org_id ? { expected_org: org_id } : undefined },
    body: { user_id: text(form, "user_id"), amount_myr: text(form, "amount_myr") },
  }));
  if (!result.ok) return { error: result.code };
  revalidatePath("/org", "layout");
  return { done: Date.now() };
}

export async function selectPackageAction(_: ActionState, form: FormData): Promise<ActionState> {
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  const kind = text(form, "kind");
  if (kind !== "free_first" && kind !== "budget_capped" && kind !== "broader") return { error: "bad_request" };
  const scenario = text(form, "scenario") === "fast" ? "fast" : "moderate";
  const result = await call(api.POST("/api/v1/org/packages/select", {
    params: org_id ? { query: { expected_org: org_id } } : undefined,
    body: { role_id: text(form, "role_id"), member_ids: form.getAll("member_id").map(String),
      scenario, kind, token: text(form, "token") },
  }));
  if (!result.ok) return { error: result.code };
  revalidatePath("/org/plan");
  revalidatePath("/app", "layout");
  revalidatePath("/work", "layout");
  return { done: Date.now() };
}

export async function acceptPackageAction(_: ActionState, form: FormData): Promise<ActionState> {
  const org_id = text(form, "org_id");
  const api = await getApi(org_id ? { workspace: org_id } : undefined);
  const result = await call(api.POST("/api/v1/org/packages/assigned/accept", {
    params: org_id ? { query: { expected_org: org_id } } : undefined,
    body: { token: text(form, "token") },
  }));
  if (!result.ok) return { error: result.code };
  revalidatePath("/app", "layout");
  revalidatePath("/work", "layout");
  return { done: Date.now() };
}
