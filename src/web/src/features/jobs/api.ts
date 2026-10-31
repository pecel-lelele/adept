import { cache } from "react";

import { call, getApi, type ScenarioId } from "@/lib/api";

/** Live openings per Adept role (counts only). Cached per request: several cards use it. */
export const fetchJobsSummary = cache(async function fetchJobsSummary(scenario: ScenarioId) {
  const api = await getApi();
  return call(api.GET("/api/v1/jobs/summary", { params: { query: { scenario } } }));
});

export const fetchRoleOpenings = cache(async function fetchRoleOpenings(
  roleId: string,
  scenario: ScenarioId,
  limit = 8,
  malaysiaFocus = false,
) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/jobs/roles/{role_id}", {
      params: { path: { role_id: roleId }, query: { scenario, limit, malaysia_focus: malaysiaFocus || undefined } },
    }),
  );
});

export const fetchCertifications = cache(async function fetchCertifications(
  roleId: string,
  scenario: ScenarioId,
  payer: "learner" | "employer" = "learner",
) {
  const api = await getApi();
  return call(api.GET("/api/v1/jobs/certifications", { params: { query: { role_id: roleId, scenario, payer } } }));
});

export async function fetchJobBoard(
  scenario: ScenarioId,
  filters: { roleId?: string; q?: string; workMode?: "onsite" | "hybrid" | "remote"; page?: number },
) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/jobs/board", {
      params: {
        query: {
          scenario,
          role_id: filters.roleId || undefined,
          q: filters.q || undefined,
          work_mode: filters.workMode,
          page: filters.page ?? 1,
        },
      },
    }),
  );
}
