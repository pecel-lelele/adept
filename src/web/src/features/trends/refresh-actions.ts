"use server";

import { call, getApi, type ApiResult, type Schemas } from "@/lib/api";

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
