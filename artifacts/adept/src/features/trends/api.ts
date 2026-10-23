import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchRadar(scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/trends/snapshot", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchRoleTrend(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/trends/roles/{role_id}", {
      params: { path: { role_id: roleId }, query: { scenario } },
    }),
  );
}

export async function fetchDataFreshness() {
  const api = await getApi();
  return call(api.GET("/api/v1/meta/data-freshness"));
}
