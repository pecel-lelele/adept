import { getSessionToken } from "@/lib/auth/session";
import { currentWorkspace } from "@/lib/auth/workspace";

import { createApiClient, type ApiClient } from "./client";

/** API client for async views; the backend forwards the httpOnly session cookie. */
export async function getApi(options?: { workspace?: string }): Promise<ApiClient> {
  const token = await getSessionToken();
  const forward: Record<string, string> = {};
  const workspace = options?.workspace ?? (token ? await currentWorkspace() : undefined);
  if (workspace) forward["X-Workspace"] = workspace;
  return createApiClient(forward);
}
