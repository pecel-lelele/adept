import type { ScenarioId } from "@/lib/api";

export const SCENARIOS = ["moderate", "fast"] as const satisfies readonly ScenarioId[];
export const DEFAULT_SCENARIO: ScenarioId = "moderate";
export const SCENARIO_PARAM = "scenario";

export type SearchParams = Record<string, string | string[] | undefined>;

/** The global scenario lives in the URL (?scenario=moderate|fast). */
export function parseScenario(value: string | string[] | undefined): ScenarioId {
  const raw = Array.isArray(value) ? value[0] : value;
  return SCENARIOS.find((s) => s === raw) ?? DEFAULT_SCENARIO;
}

export function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
