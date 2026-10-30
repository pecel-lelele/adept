"use server";

import { headers } from "next/headers";

import { API_URL } from "@/lib/api/client";
import { trustedClientIp } from "@/lib/api/proxy";
import { proxyConfig } from "@/lib/api/proxy-config";
import { getSessionToken } from "@/lib/auth/session";

/**
 * Admin trend refresh (F2). The browser never sees the GitHub token: these server actions
 * forward the signed session to the API, which checks ADMIN_EMAILS and dispatches the
 * trends-refresh workflow itself. Types mirror app/contracts/trends.py until the generated
 * client includes them.
 */
export type RefreshStatus = {
  status: "queued" | "in_progress" | "completed";
  conclusion?: string | null;
  run_id?: number | null;
  run_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  dispatched?: boolean;
  already_running?: boolean;
  caches_cleared?: boolean;
  snapshot_date?: string | null;
  served_from?: "db" | "fixture" | null;
  is_fallback?: boolean;
};

export type RescoreResult = {
  status: "published" | "no_new_data" | "failed";
  message: string;
  snapshot_date?: string | null;
  observed_from?: string | null;
  observed_to?: string | null;
};

export type Outcome<T> = { ok: true; data: T } | { ok: false; status: number; code: string };

const CODE = /^[a-z][a-z0-9_]{0,63}$/;

async function forward(): Promise<Record<string, string>> {
  const out: Record<string, string> = { Accept: "application/json", "X-Workspace": "personal" };
  const token = await getSessionToken();
  if (token) out["X-Demo-User"] = token;
  const { secret, trustedHops, clientIpMode } = proxyConfig();
  if (secret) {
    const ip = trustedClientIp((await headers()).get("x-forwarded-for"), trustedHops, clientIpMode);
    if (ip) {
      out["X-Real-IP"] = ip;
      out["X-Internal-Proxy-Secret"] = secret;
    }
  }
  return out;
}

async function request<T>(method: "GET" | "POST", path: string, timeoutMs: number): Promise<Outcome<T>> {
  try {
    const response = await fetch(API_URL + path, {
      method,
      headers: await forward(),
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(timeoutMs),
    });
    const body: unknown = await response.json().catch(() => null);
    if (response.ok) return { ok: true, data: body as T };
    let code = response.status >= 500 ? "server_error" : "error";
    if (body && typeof body === "object" && "error" in body) {
      const error: unknown = body.error;
      if (error && typeof error === "object" && "code" in error && typeof error.code === "string" && CODE.test(error.code)) {
        code = error.code;
      }
    }
    return { ok: false, status: response.status, code };
  } catch {
    return { ok: false, status: 0, code: "network" };
  }
}

/** Fetch latest data: start (or join) the trends-refresh workflow run. */
export async function startTrendRefresh(): Promise<Outcome<RefreshStatus>> {
  return request<RefreshStatus>("POST", "/api/v1/trends/refresh", 30000);
}

/** Poll a run; the API clears its trend caches once the run succeeds. */
export async function trendRefreshStatus(runId: number | null): Promise<Outcome<RefreshStatus>> {
  const query = runId !== null && Number.isSafeInteger(runId) && runId > 0 ? `?run_id=${runId}` : "";
  return request<RefreshStatus>("GET", `/api/v1/trends/refresh/status${query}`, 20000);
}

/** Re-score the stored signals (no ingest, no model call). */
export async function rescoreTrends(): Promise<Outcome<RescoreResult>> {
  return request<RescoreResult>("POST", "/api/v1/trends/refresh/rescore", 120000);
}
