import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchMyOrg() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/me"));
}

export async function fetchMembers() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/members"));
}

export async function fetchGaps(scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/org/gaps", { params: { query: { scenario } } }));
}

export async function fetchPlan() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/plan"));
}
