import { useTranslations } from "next-intl";

import type { ScenarioId } from "@/lib/api";

export function ScenarioDelta({ score, otherScore, otherScenario }: { score: number; otherScore?: number; otherScenario: ScenarioId }) {
  const t = useTranslations("matching");
  const ts = useTranslations("common.scenario");
  if (otherScore === undefined) return null;
  const delta = (score - otherScore) * 100;
  const rounded = Math.round(delta * 10) / 10;
  return (
    <span className="a-chip" data-tone={rounded > 0 ? "up" : rounded < 0 ? "down" : undefined}>
      {t("scenarioDelta", { delta: `${rounded > 0 ? "+" : ""}${rounded.toFixed(1)}`, scenario: ts(`${otherScenario}Short`) })}
    </span>
  );
}
