import { useTranslations } from "next-intl";

import type { ScenarioId } from "@/lib/api";

export function ScenarioDelta({ score, rank, otherScore, otherRank, otherScenario }: {
  score: number; rank?: number | null; otherScore?: number | null;
  otherRank?: number | null; otherScenario?: ScenarioId | null;
}) {
  const t = useTranslations("matching");
  const ts = useTranslations("common.scenario");
  if (otherScore == null || !otherScenario) return null;
  const rounded = Math.round((score - otherScore) * 1000) / 10;
  const movement = rank != null && otherRank != null ? otherRank - rank : null;
  return (
    <span className="a-chip" data-tone={movement != null ? (movement > 0 ? "up" : movement < 0 ? "down" : undefined) : (rounded > 0 ? "up" : rounded < 0 ? "down" : undefined)}>
      {movement != null ? t("scenarioRankDelta", { movement: `${movement > 0 ? "▲" : movement < 0 ? "▼" : "↔"}${Math.abs(movement)}`, scenario: ts(`${otherScenario}Short`) }) : t("scenarioDelta", { delta: `${rounded > 0 ? "+" : ""}${rounded.toFixed(1)}`, scenario: ts(`${otherScenario}Short`) })}
      {" · "}{t("otherScenarioScore", { score: (otherScore * 100).toFixed(1) })}
      {otherRank != null ? ` · ${t("otherScenarioRank", { rank: otherRank })}` : ""}
    </span>
  );
}
