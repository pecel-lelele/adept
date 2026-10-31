import { call, getApi, type ScenarioId } from "@/lib/api";

import type { TrendKind, TrendMode, TrendPreset } from "./range";

export async function fetchRadar(scenario: ScenarioId, snapshotDate?: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/trends/snapshot", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchRoleDirections(scenario: ScenarioId, snapshotDate: string) {
  const api = await getApi();
  return call(api.GET("/api/v1/trends/radar", { params: { query: { scenario, snapshot_date: snapshotDate } } }));
}

export async function fetchDataFreshness() {
  const api = await getApi();
  return call(api.GET("/api/v1/meta/data-freshness"));
}

export async function fetchCompare(query: {
  kind: TrendKind;
  entities: string[];
  preset?: TrendPreset;
  start?: string;
  end?: string;
  scenario: ScenarioId;
  horizon: number;
  mode: TrendMode;
}) {
  const api = await getApi();
  return call(
    api.GET("/api/v1/trends/compare", {
      params: {
        query: {
          kind: query.kind,
          entities: query.entities,
          preset: query.preset,
          start: query.start,
          end: query.end,
          scenario: query.scenario,
          horizon_days: query.horizon,
          mode: query.mode,
        },
      },
    }),
  );
}
