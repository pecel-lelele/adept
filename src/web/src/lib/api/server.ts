import { getDemoUser } from "@/lib/auth/session";

import { createApiClient, type ApiClient } from "./client";

/** API client for Server Components; forwards the demo persona to the API. */
export async function getApi(): Promise<ApiClient> {
  const user = await getDemoUser();
  return createApiClient(user ? { "X-Demo-User": user } : {});
}
