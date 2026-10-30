import { headers } from "next/headers";

import { getSessionToken } from "@/lib/auth/session";
import { currentWorkspace } from "@/lib/auth/workspace";

import { createApiClient, type ApiClient } from "./client";
import { proxyConfig } from "./proxy-config";
import { clientIpHeaders } from "./proxy";

export { trustedClientIp } from "./proxy";

/** Shared with the API (PROXY_SHARED_SECRET) so it trusts the X-Real-IP we forward. */
const proxy = proxyConfig();
/** API client for Server Components; forwards the session token and client IP to the API. */
export async function getApi(options?: { workspace?: string }): Promise<ApiClient> {
  const token = await getSessionToken();
  const forward: Record<string, string> = token ? { "X-Demo-User": token } : {};
  const workspace = options?.workspace ?? (token ? await currentWorkspace() : undefined);
  if (workspace) forward["X-Workspace"] = workspace;
  Object.assign(forward, clientIpHeaders((await headers()).get("x-forwarded-for"), proxy));
  return createApiClient(forward);
}
