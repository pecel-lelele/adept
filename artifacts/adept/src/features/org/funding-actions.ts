import type { ActionState } from "@/features/pathway/action-state";
import { rpc } from "@/lib/next-compat/rpc";

const M = "features/org/funding-actions.ts";

/** HR sets a member's yearly training budget (used to build the budget-capped package). */
export async function budgetAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "budgetAction", [state, form]);
}
export async function selectPackageAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "selectPackageAction", [state, form]);
}
export async function acceptPackageAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "acceptPackageAction", [state, form]);
}
