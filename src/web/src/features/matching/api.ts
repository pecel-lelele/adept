import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchMatches(scenario: ScenarioId, snapshotDate?: string, sdgWeight = 0) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/matches", {
      params: { query: { scenario, snapshot_date: snapshotDate, sdg_weight: sdgWeight || undefined } },
    }),
  );
}

/** Trend replay: ranking on an older snapshot vs the latest, with the skills that moved it. */
export async function fetchReplay(scenario: ScenarioId, fromDate: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/matches/replay", { params: { query: { scenario, from_date: fromDate } } }));
}

export async function fetchMatch(roleId: string, scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/matches/{role_id}", {
      params: { path: { role_id: roleId }, query: { scenario, snapshot_date: snapshotDate } },
    }),
  );
}
