import { cache } from "react";

import { call, createApiClient, type Schemas } from "@/lib/api";

import { getSessionToken } from "./session";

import { selectedOrg } from "./workspace";

export type WorkspaceOption = Schemas["Workspace"];

/** Workspaces the signed-in person can switch to (personal first). Cached for one render. */
export const getWorkspaces = cache(async (): Promise<WorkspaceOption[]> => {
  // Membership discovery belongs to the account. A removed/stale selected organisation must
  // not prevent the person finding their remaining workspaces.
  const token = await getSessionToken();
  if (!token) return [];
  const api = createApiClient({ "X-Demo-User": token });
  const result = await call(api.GET("/api/v1/org/workspaces"));
  return result.ok ? result.data.workspaces : [];
});

/**
 * The organisation workspace to show on /work or /org: the remembered one if the person still
 * belongs to it with a fitting role, else their first such organisation.
 */
export async function pickOrg(
  roles: readonly ("member" | "manager" | "advisor")[],
): Promise<{ chosen?: WorkspaceOption; remembered?: WorkspaceOption; fallback?: WorkspaceOption }> {
  const spaces = (await getWorkspaces()).filter((w) => w.kind === "org");
  const wanted = await selectedOrg();
  const remembered = spaces.find((w) => w.id === wanted);
  const fallback = spaces.find((w) => w.role && roles.includes(w.role));
  const chosen = remembered && remembered.role && roles.includes(remembered.role) ? remembered : undefined;
  return { chosen, remembered, fallback };
}
