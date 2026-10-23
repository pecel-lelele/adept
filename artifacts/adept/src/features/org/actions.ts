import { rpc } from "@/lib/next-compat/rpc";

const M = "features/org/actions.ts";

export type OrgActionState = { error?: string; done?: number };

export async function updateOrgAction(state: OrgActionState, form: FormData): Promise<OrgActionState> {
  return rpc(M, "updateOrgAction", [state, form]);
}
export async function rotateCodeAction(expectedOrg?: string): Promise<OrgActionState> {
  return rpc(M, "rotateCodeAction", [expectedOrg]);
}
export async function removeMemberAction(memberId: string, expectedOrg?: string): Promise<OrgActionState> {
  return rpc(M, "removeMemberAction", [memberId, expectedOrg]);
}
