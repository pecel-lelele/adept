import type { ActionState } from "@/features/pathway/action-state";
import { rpc } from "@/lib/next-compat/rpc";

const M = "features/org/work/actions.ts";

/** The member accepts, declines (optional programmes only) or asks to change an agreement. */
export async function decideProgrammeAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "decideProgrammeAction", [state, form]);
}
/** The member turns skill-level sharing with this organisation on or off. */
export async function setSharingAction(state: ActionState, form: FormData): Promise<ActionState> {
  return rpc(M, "setSharingAction", [state, form]);
}
