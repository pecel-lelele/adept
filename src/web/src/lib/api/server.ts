import { headers } from "next/headers";

import { getDemoUser } from "@/lib/auth/session";

import { createApiClient, type ApiClient } from "./client";

/** Shared with the API (PROXY_SHARED_SECRET) so it trusts the X-Real-IP we forward. */
const PROXY_SECRET = process.env.PROXY_SHARED_SECRET ?? "";

/** The browser's address as seen by this server, for per-client rate limiting in the API. */
async function clientIp(): Promise<string | undefined> {
  const incoming = await headers();
  const forwarded = incoming.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || incoming.get("x-real-ip") || undefined;
}

/** API client for Server Components; forwards the demo persona and client IP to the API. */
export async function getApi(): Promise<ApiClient> {
  const user = await getDemoUser();
  const forward: Record<string, string> = user ? { "X-Demo-User": user } : {};
  if (PROXY_SECRET) {
    const ip = await clientIp();
    if (ip) {
      forward["X-Real-IP"] = ip;
      forward["X-Internal-Proxy-Secret"] = PROXY_SECRET;
    }
  }
  return createApiClient(forward);
}
