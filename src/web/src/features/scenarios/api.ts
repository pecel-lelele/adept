import { call, getApi } from "@/lib/api";

export async function fetchScenarios() {
  const api = await getApi();
  return call(api.GET("/api/v1/scenarios"));
}

export async function fetchOutlook(roleId: string, snapshotDate?: string) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/scenarios/outlook", { params: { query: { role_id: roleId, snapshot_date: snapshotDate } } }),
  );
}
