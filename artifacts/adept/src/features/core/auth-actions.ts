import { rpc } from "@/lib/next-compat/rpc";

const M = "features/core/auth-actions.ts";

export type AuthState = { error?: string; values?: Record<string, string> };

export async function signupAction(state: AuthState, form: FormData): Promise<AuthState> {
  return rpc(M, "signupAction", [state, form]);
}
export async function loginAction(state: AuthState, form: FormData): Promise<AuthState> {
  return rpc(M, "loginAction", [state, form]);
}
export async function joinOrgAction(state: AuthState, form: FormData): Promise<AuthState> {
  return rpc(M, "joinOrgAction", [state, form]);
}
export async function signOutAction(): Promise<void> {
  return rpc(M, "signOutAction", []);
}
/** Permanently delete the signed-in account after the API re-checks the password. */
export async function deleteAccountAction(state: AuthState, form: FormData): Promise<AuthState> {
  return rpc(M, "deleteAccountAction", [state, form]);
}
