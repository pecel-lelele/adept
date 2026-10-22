"use server";

import { revalidatePath } from "next/cache";
import { call, getApi } from "@/lib/api";
import type { ActionState } from "@/features/pathway/action-state";

const text = (f: FormData, key: string) => String(f.get(key) ?? "").trim();

export async function fundingAction(_: ActionState, form: FormData): Promise<ActionState> {
  const api = await getApi();
  const year = Number(text(form, "year"));
  const claim_id = text(form, "claim_id");
  const revision = Number(text(form, "revision"));
  const op = text(form, "op");
  let result;
  if (op === "budget") {
    result = await call(api.PUT("/api/v1/org/funding/{year}/budget", {
      params: { path: { year } },
      body: { user_id: text(form, "user_id"), amount_myr: text(form, "amount_myr") },
    }));
  } else if (op === "request") {
    result = await call(api.POST("/api/v1/org/funding/{year}/requests", {
      params: { path: { year } },
      body: { course_id: text(form, "course_id"), role_id: text(form, "role_id"),
        amount_myr: text(form, "amount_myr"), quote_url: text(form, "quote_url") },
    }));
  } else if (op === "completion") {
    result = await call(api.POST("/api/v1/org/funding/{year}/requests/{claim_id}/completion", {
      params: { path: { year, claim_id } }, body: { revision, url: text(form, "certificate_url") },
    }));
  } else if (op === "submit") {
    result = await call(api.POST("/api/v1/org/funding/{year}/requests/{claim_id}/submit", {
      params: { path: { year, claim_id } },
      body: { revision, amount_myr: text(form, "amount_myr"), receipt_url: text(form, "receipt_url"),
        receipt_reference: text(form, "receipt_reference"),
        purchased_at: text(form, "purchased_at") + "+08:00" },
    }));
  } else if (["approve", "reject", "cancel", "accept_claim", "mark_paid"].includes(op)) {
    result = await call(api.POST("/api/v1/org/funding/{year}/requests/{claim_id}/decision", {
      params: { path: { year, claim_id } },
      body: { revision, action: op as "approve" | "reject" | "cancel" | "accept_claim" | "mark_paid",
        note: text(form, "note"), payment_reference: text(form, "payment_reference") },
    }));
  } else return { error: "Unknown action." };
  if (!result.ok) return { error: result.message };
  revalidatePath("/org", "layout");
  revalidatePath("/app", "layout");
  return { done: Date.now() };
}

export async function selectPackageAction(_: ActionState, form: FormData): Promise<ActionState> {
  const api = await getApi();
  const kind = text(form, "kind");
  if (kind !== "free_first" && kind !== "budget_capped" && kind !== "broader") return { error: "Invalid package." };
  const scenario = text(form, "scenario") === "fast" ? "fast" : "moderate";
  const result = await call(api.POST("/api/v1/org/packages/select", {
    body: { role_id: text(form, "role_id"), member_ids: form.getAll("member_id").map(String),
      scenario, kind, token: text(form, "token") },
  }));
  if (!result.ok) return { error: result.message };
  revalidatePath("/org/plan");
  revalidatePath("/app", "layout");
  return { done: Date.now() };
}

export async function acceptPackageAction(_: ActionState, form: FormData): Promise<ActionState> {
  const api = await getApi();
  const result = await call(api.POST("/api/v1/org/packages/assigned/accept", {
    body: { token: text(form, "token") },
  }));
  if (!result.ok) return { error: result.message };
  revalidatePath("/app", "layout");
  return { done: Date.now() };
}
