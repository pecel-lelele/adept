import { cache } from "react";

import { call, getApi, type ScenarioId } from "@/lib/api";

/** Cached for one server render: the layout and the page both read it. */
export const fetchMyOrg = cache(async function fetchMyOrg() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/me"));
});

/** Cached for one server render: the sidebar ticks and the dashboard both read it. */
export const fetchMembers = cache(async function fetchMembers() {
  const api = await getApi();
  return call(api.GET("/api/v1/org/members"));
});

export async function fetchGaps(scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/org/gaps", { params: { query: { scenario } } }));
}

export async function fetchPlan(scenario: ScenarioId, roleId?: string) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/org/plan", {
      params: { query: { scenario, role_id: roleId } },
    }),
  );
}
