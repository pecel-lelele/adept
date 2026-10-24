import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./types";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 15000;

export type ApiClient = Client<paths>;

/** Typed API client. Paths, params and responses come from the generated OpenAPI types. */
export function createApiClient(headers: Record<string, string> = {}): ApiClient {
  return createClient<paths>({
    baseUrl: API_URL,
    headers,
    cache: "no-store",
    fetch: (request) => fetchWithRetry(request),
  });
}

/** Retry reads once on a dropped connection or a transient gateway/database outage. */
async function fetchWithRetry(request: Request): Promise<Response> {
  const retryable = request.method === "GET" || request.method === "HEAD";
  const attempt = () => fetch(request.clone(), { signal: AbortSignal.timeout(TIMEOUT_MS) });
  try {
    const response = await attempt();
    if (!retryable || ![502, 503, 504].includes(response.status)) return response;
    // Release the failed response before retrying. Writes are never replayed: a lost
    // acknowledgement does not tell us whether a transaction committed.
    await response.body?.cancel();
  } catch (error) {
    if (!retryable) throw error;
  }
  await new Promise((resolve) => setTimeout(resolve, 300));
  return attempt();
}

/** Machine-readable reason a call failed; pages use it to offer the right next step. */
export type ApiFailure = {
  ok: false;
  message: string;
  status: number;
  /** API error code, e.g. "profile_required", "unauthorized", or "network". */
  code: string;
};

export type ApiResult<T> = { ok: true; data: T } | ApiFailure;

/** Turn an openapi-fetch call into a result, also catching "API not running". */
export async function call<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<ApiResult<T>> {
  try {
    const { data, error, response } = await request;
    if (response.ok) return { ok: true, data: data as T };
    return { ok: false, status: response.status, ...errorBody(error, response.status) };
  } catch {
    return {
      ok: false,
      status: 0,
      code: "network",
      message: "We couldn’t reach Adept right now. Please try again in a moment.",
    };
  }
}

/** The API always answers errors as {"error": {"code", "message"}}. */
export function errorBody(error: unknown, status: number): { code: string; message: string } {
  if (error && typeof error === "object" && "error" in error) {
    const body = (error as { error?: { code?: string; message?: string } }).error;
    if (body?.message) return { code: body.code ?? "error", message: body.message };
  }
  if (status === 401) return { code: "unauthorized", message: "Please sign in again." };
  if (status >= 500) {
    return { code: "server_error", message: "Something went wrong on our side. Please try again." };
  }
  return { code: "error", message: `Request failed (${status}).` };
}
