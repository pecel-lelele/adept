import { cache } from "react";

import { call, createApiClient, type ApiResult, type Schemas } from "@/lib/api";

import { getSessionToken } from "./session";

import { selectedOrg } from "./workspace";

export type WorkspaceOption = Schemas["Workspace"];

/** Workspaces the signed-in person can switch to (personal first). Cached for one render. */
export const getWorkspaceResult = cache(async (): Promise<ApiResult<Schemas["WorkspaceList"]>> => {
  // Membership discovery belongs to the account. A removed/stale selected organisation must
  // not prevent the person finding their remaining workspaces.
  const token = await getSessionToken();
  if (!token) return { ok: false, status: 401, code: "unauthorized" };
  const api = createApiClient({ "X-Demo-User": token });
  return call(api.GET("/api/v1/org/workspaces"));
});

export const getWorkspaces = cache(async (): Promise<WorkspaceOption[]> => {
  const result = await getWorkspaceResult();
  return result.ok ? result.data.workspaces : [];
});

/**
 * The organisation workspace to show on /work or /org: the remembered one if the person still
 * belongs to it with a fitting role, else their first such organisation.
 */
export async function pickOrg(
  roles: readonly ("member" | "manager" | "advisor")[],
): Promise<{ chosen?: WorkspaceOption; remembered?: WorkspaceOption; fallback?: WorkspaceOption; failure?: Extract<ApiResult<never>, { ok: false }> }> {
  const result = await getWorkspaceResult();
  if (!result.ok) return { failure: result };
  const spaces = result.data.workspaces.filter((w) => w.kind === "org");
  const wanted = await selectedOrg();
  const remembered = spaces.find((w) => w.id === wanted);
  const fallback = spaces.find((w) => w.role && roles.includes(w.role));
  const chosen = remembered && remembered.role && roles.includes(remembered.role) ? remembered : undefined;
  return { chosen, remembered, fallback };
}
