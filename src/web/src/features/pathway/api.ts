import { call, getApi, type ScenarioId } from "@/lib/api";
import { cache } from "react";

export async function fetchPathway(
  roleId: string,
  scenario: ScenarioId,
  snapshotDate?: string,
) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/pathway", {
      params: {
        query: { role_id: roleId, scenario, snapshot_date: snapshotDate },
      },
    }),
  );
}

export const fetchPlanStatus = cache(async function fetchPlanStatus() {
  const api = await getApi();
  return call(api.GET("/api/v1/pathway/plans/me"));
});

export async function fetchProgress(roleId: string, scenario: ScenarioId) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/pathway/progress", {
      params: { query: { role_id: roleId, scenario } },
    }),
  );
}

export async function fetchCompare(
  scenario: ScenarioId,
  roleIds: string[] = [],
  snapshotDate?: string,
) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/pathway/compare", {
      params: {
        query: {
          scenario,
          snapshot_date: snapshotDate,
          ...(roleIds.length ? { role_ids: roleIds } : {}),
        },
      },
    }),
  );
}

/** The role the learner chose (their saved plan), or null when they have not chosen yet. */
export async function savedRoleId(): Promise<string | null> {
  const status = await fetchPlanStatus();
  return status.ok ? (status.data.saved?.role_id ?? null) : null;
}
