import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./types";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type ApiClient = Client<paths>;

/** Typed API client. Paths, params and responses come from the generated OpenAPI types. */
export function createApiClient(headers: Record<string, string> = {}): ApiClient {
  return createClient<paths>({ baseUrl: API_URL, headers, cache: "no-store" });
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; message: string };

/** Turn an openapi-fetch call into a result, also catching "API not running". */
export async function call<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<ApiResult<T>> {
  try {
    const { data, error, response } = await request;
    if (data !== undefined) return { ok: true, data };
    return { ok: false, message: errorMessage(error, response.status) };
  } catch {
    return { ok: false, message: `API unreachable at ${API_URL}. Is \`make dev\` running?` };
  }
}

function errorMessage(error: unknown, status: number): string {
  if (error && typeof error === "object" && "error" in error) {
    const body = (error as { error?: { message?: string } }).error;
    if (body?.message) return `${status}: ${body.message}`;
  }
  return `Request failed with status ${status}`;
}
