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

export async function fetchSeries(query: { start?: string; end?: string; skillIds: string[]; scenario: ScenarioId }) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/trends/series", {
      params: { query: { start: query.start, end: query.end, skill_ids: query.skillIds, scenario: query.scenario } },
    }),
  );
}
