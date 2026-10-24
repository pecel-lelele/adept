import { headers } from "next/headers";

import { getSessionToken } from "@/lib/auth/session";
import { currentWorkspace } from "@/lib/auth/workspace";

import { createApiClient, type ApiClient } from "./client";
import { proxyConfig } from "./proxy-config";

/** Shared with the API (PROXY_SHARED_SECRET) so it trusts the X-Real-IP we forward. */
const { secret: PROXY_SECRET, trustedHops: TRUSTED_PROXY_HOPS } = proxyConfig();
/**
 * Number of trusted proxies in front of this server that *append* to X-Forwarded-For
 * (e.g. 1 for a single platform load balancer). The client controls everything to the left
 * of what those proxies append, so only the entry they added can be trusted.
 * 0 (default) = no trusted proxy: never forward an address.
 */

/** The client address as recorded by our nearest trusted proxy, or undefined. */
export function trustedClientIp(forwardedFor: string | null, hops: number): string | undefined {
  if (!forwardedFor || hops <= 0) return undefined;
  const chain = forwardedFor
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  // The last `hops` proxies each appended the address they received the request from;
  // the entry `hops` from the end is the client as seen by the outermost trusted proxy.
  return chain.length >= hops ? chain[chain.length - hops] : undefined;
}

/** API client for Server Components; forwards the session token and client IP to the API. */
export async function getApi(options?: { workspace?: string }): Promise<ApiClient> {
  const token = await getSessionToken();
  const forward: Record<string, string> = token ? { "X-Demo-User": token } : {};
  const workspace = options?.workspace ?? (token ? await currentWorkspace() : undefined);
  if (workspace) forward["X-Workspace"] = workspace;
  if (PROXY_SECRET) {
    const ip = trustedClientIp((await headers()).get("x-forwarded-for"), TRUSTED_PROXY_HOPS);
    if (ip) {
      forward["X-Real-IP"] = ip;
      forward["X-Internal-Proxy-Secret"] = PROXY_SECRET;
    }
  }
  return createApiClient(forward);
}
