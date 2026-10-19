"use client";

import { useSearchParams } from "next/navigation";

import type { ScenarioId } from "@/lib/api";
import { parseScenario, SCENARIO_PARAM } from "@/lib/scenario";

/** Current scenario from the URL, for client components. */
export function useScenario(): ScenarioId {
  return parseScenario(useSearchParams().get(SCENARIO_PARAM) ?? undefined);
}
