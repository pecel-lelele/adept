import { call, createApiClient, type Schemas } from "@/lib/api";
import { getGeneration } from "@/lib/next-compat/router";

import { getSessionToken } from "./session";

import { selectedOrg } from "./workspace";

export type WorkspaceOption = Schemas["Workspace"];

let cached: { generation: number; promise: Promise<WorkspaceOption[]> } | undefined;

/** Workspaces the signed-in person can switch to (personal first). Cached until refresh. */
export function getWorkspaces(): Promise<WorkspaceOption[]> {
  const generation = getGeneration();
  if (!cached || cached.generation !== generation) {
    const promise = (async () => {
      // Membership discovery belongs to the account. A removed/stale selected organisation must
      // not prevent the person finding their remaining workspaces.
      if (!(await getSessionToken())) return [];
      const api = createApiClient();
      const result = await call(api.GET("/api/v1/org/workspaces"));
      return result.ok ? result.data.workspaces : [];
    })();
    cached = { generation, promise };
  }
  return cached.promise;
}

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
