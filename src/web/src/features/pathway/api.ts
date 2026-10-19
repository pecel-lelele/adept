import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchPathway(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/pathway", { params: { query: { role_id: roleId, scenario } } }));
}

export async function fetchPlanStatus() {
  const api = await getApi();
  return call(api.GET("/api/v1/pathway/plans/me"));
}

export async function fetchProgress(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/pathway/progress", { params: { query: { role_id: roleId, scenario } } }),
  );
}
