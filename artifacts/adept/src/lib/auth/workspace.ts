import { cookies, headers } from "next/headers";

/**
 * Workspaces (M4-033). One account works in a personal workspace (/app) and in each organisation
 * it belongs to: as a member (/work) or as a manager (/org). The page path decides personal vs
 * organisation; this cookie remembers which organisation. The API checks the membership on
 * every request, so a forged cookie only yields 403.
 */
export const ORG_COOKIE = "adept_org";
export const PERSONAL = "personal";
const ORG_ID = /^[A-Za-z0-9_-]{1,80}$/;

export function isOrgId(value: string | null | undefined): value is string {
  return !!value && value !== PERSONAL && ORG_ID.test(value);
}

/** X-Workspace for a page path: personal for /app, the chosen organisation for /work and /org. */
export function workspaceFor(path: string, org: string | undefined): string | undefined {
  if (path === "/app" || path.startsWith("/app/")) return PERSONAL;
  if (/^\/(work|org)(\/|$)/.test(path)) return org;
  return undefined;
}

export async function selectedOrg(): Promise<string | undefined> {
  const value = (await cookies()).get(ORG_COOKIE)?.value;
  return isOrgId(value) ? value : undefined;
}

/** The workspace of the page being rendered (server components and server actions). */
export async function currentWorkspace(): Promise<string | undefined> {
  const path = (await headers()).get("x-adept-path") ?? "";
  return workspaceFor(path, await selectedOrg());
}
