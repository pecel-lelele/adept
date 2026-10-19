import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchMatches(scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/matches", { params: { query: { scenario } } }));
}

export async function fetchMatch(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/matches/{role_id}", {
      params: { path: { role_id: roleId }, query: { scenario } },
    }),
  );
}
