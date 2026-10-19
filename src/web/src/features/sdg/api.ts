import { call, getApi, type ScenarioId } from "@/lib/api";

export async function fetchMyContribution(roleId: string | undefined, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/sdg/contribution/me", {
      params: { query: { scenario, ...(roleId ? { role_id: roleId } : {}) } },
    }),
  );
}

export async function fetchOrgContribution(scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/sdg/contribution/org", { params: { query: { scenario } } }));
}

export async function fetchRegionContribution(state: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/sdg/contribution/region/{state}", {
      params: { path: { state }, query: { scenario } },
    }),
  );
}

export async function fetchRegions() {
  const api = await getApi();
  return call(api.GET("/api/v1/sdg/regions"));
}

export async function fetchRoleSdg(roleId: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/sdg/roles/{role_id}", { params: { path: { role_id: roleId } } }));
}
