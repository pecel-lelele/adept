"use server";

import { call, getApi, type ApiResult, type Schemas } from "@/lib/api";
import type { ApiFailure } from "@/lib/api/client";

export type RefreshRun = Schemas["BackgroundRefresh"];
export type RefreshReply = { ok: true; data: RefreshRun } | (ApiFailure & { retryAt?: string });

export async function checkRefresh(): Promise<RefreshReply> {
  try {
    const api = await getApi({ workspace: "personal", timeoutMs: 10000 });
    const response = await api.POST("/api/v1/data/refresh/check", { body: { bypass_cooldown: false } });
    const result = await call(Promise.resolve(response));
    const retry = response.response.headers.get("retry-after");
    if (!result.ok && result.status === 429 && retry && Number.isFinite(Number(retry))) {
      return { ...result, retryAt: new Date(Date.now() + Number(retry) * 1000).toISOString() };
    }
    return result;
  } catch {
    return { ok: false, status: 0, code: "network" };
  }
}

export async function pollRefresh(runId: string): Promise<ApiResult<RefreshRun>> {
  try {
    const api = await getApi({ workspace: "personal", timeoutMs: 10000 });
    return await call(api.GET("/api/v1/data/refresh/status/{run_id}", { params: { path: { run_id: runId } } }));
  } catch {
    return { ok: false, status: 0, code: "network" };
  }
}

// Legacy workflow/rescore actions remain available until automatic publication is proven.
export type RefreshStatus = Schemas["TrendRefreshStatus"];
export type RescoreResult = Schemas["TrendRescoreResult"];
export type Outcome<T> = ApiResult<T>;

export async function startTrendRefresh(): Promise<Outcome<RefreshStatus>> {
  const api = await getApi({ workspace: "personal", timeoutMs: 30000 });
  return call(api.POST("/api/v1/trends/refresh"));
}

export async function trendRefreshStatus(runId: number | null): Promise<Outcome<RefreshStatus>> {
  const api = await getApi({ workspace: "personal", timeoutMs: 20000 });
  return call(api.GET("/api/v1/trends/refresh/status", {
    params: { query: { run_id: runId !== null && Number.isSafeInteger(runId) && runId > 0 ? runId : undefined } },
  }));
}

export async function rescoreTrends(): Promise<Outcome<RescoreResult>> {
  const api = await getApi({ workspace: "personal", timeoutMs: 120000 });
  return call(api.POST("/api/v1/trends/refresh/rescore"));
}
