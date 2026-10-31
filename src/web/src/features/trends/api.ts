import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchRadar(scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/trends/snapshot", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchRoleDirections(scenario: ScenarioId, snapshotDate: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/trends/radar", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchDataFreshness() {
  const api = await getApi();
  return call(api.GET("/api/v1/meta/data-freshness"));
}
