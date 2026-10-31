import { call, getApi, type ApiResult } from "@/lib/api";
import type { ImpactSummary } from "./types";

/** Public reference/synthetic evidence; the API never reads the caller's personal profile. */
export async function fetchImpact(): Promise<ApiResult<ImpactSummary>> {
  const api = await getApi({ timeoutMs: 20000 });
  return call(api.GET("/api/v1/impact/summary"));
}
