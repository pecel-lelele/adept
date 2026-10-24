import { useTranslations } from "next-intl";

import type { ScenarioId } from "@/lib/api";

/** Every prediction is labelled as an estimate, with its scenario. */
export function EstimateLabel({ scenario, isEstimate = true }: { scenario?: ScenarioId; isEstimate?: boolean }) {
  const t = useTranslations("common");
  if (!isEstimate) return null;
  return (
    <span className="a-estimate-label" title={t("estimate.hint")}>
      {t("estimate.label")}
      {scenario ? ` · ${t(`scenario.${scenario}`)}` : null}
    </span>
  );
}
