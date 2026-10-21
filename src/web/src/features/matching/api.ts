import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchMatches(scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/matches", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchMatch(roleId: string, scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/matches/{role_id}", {
      params: { path: { role_id: roleId }, query: { scenario, snapshot_date: snapshotDate } },
    }),
  );
}
