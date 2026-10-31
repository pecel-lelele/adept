import { call, getApi, type ApiResult, type Schemas } from "@/lib/api";

export type DataSourceId = Schemas["DataSourceFreshness"]["source"];
export type RefreshableSource = Schemas["DataRefreshResult"]["source"];
export type RefreshRunSummary = Schemas["RefreshRunSummary"];
export type DataSourceFreshness = Schemas["DataSourceFreshness"];
export type DataFreshnessResponse = Schemas["DataFreshnessResponse"];
export type DataRefreshResult = Schemas["DataRefreshResult"];

const REFRESHABLE = ["courses", "catalogue", "jobs", "labour", "trends"] as const;
function isRefreshable(source: string): source is RefreshableSource {
  return (REFRESHABLE as readonly string[]).includes(source);
}

export async function fetchDataSources(): Promise<ApiResult<DataFreshnessResponse>> {
  const api = await getApi({ timeoutMs: 10000 });
  return call(api.GET("/api/v1/data/freshness"));
}

export async function postDataRefresh(source: string): Promise<ApiResult<DataRefreshResult>> {
  if (!isRefreshable(source)) return { ok: false, status: 422, code: "validation_error" };
  const api = await getApi({ workspace: "personal", timeoutMs: 315000 });
  return call(api.POST("/api/v1/data/refresh/{source}", { params: { path: { source } } }));
}

export async function fetchRecentRefreshes(): Promise<ApiResult<Schemas["RefreshHistory"]>> {
  const api = await getApi();
  return call(api.GET("/api/v1/data/refresh/recent"));
}
