import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchPathway(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/pathway", { params: { query: { role_id: roleId, scenario } } }));
}
