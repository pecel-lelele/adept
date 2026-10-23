import { rpc } from "@/lib/next-compat/rpc";

import type { ActionState } from "./action-state";

const M = "features/pathway/actions.ts";

/** The learner explicitly chooses a target role and saves its plan (human in charge). */
export async function savePlanAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "savePlanAction", [state, form]);
}
export async function acceptReplanAction(): Promise<ActionState> {
  return rpc(M, "acceptReplanAction", []);
}
export async function updateProgressAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "updateProgressAction", [state, form]);
}
/** Learner attaches a certificate link; the API checks it against the provider's pages. */
export async function submitEvidenceAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "submitEvidenceAction", [state, form]);
}
/** HR / advisor confirms or rejects a member's completion. */
export async function reviewCompletionAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "reviewCompletionAction", [state, form]);
}
/** Member, in the organisation workspace: share a personally completed course with the programme. */
export async function shareCompletionAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "shareCompletionAction", [state, form]);
}
