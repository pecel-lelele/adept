import { useTranslations } from "next-intl";

import type { RecommendationMeta } from "@/lib/api";

/** Every prediction is labelled as an estimate, with its scenario. */
export function EstimateLabel({ scenario, isEstimate = true, historical = false }: { scenario?: RecommendationMeta["scenario"]; isEstimate?: boolean; historical?: boolean }) {
  const t = useTranslations("common");
  if (!isEstimate) return null;
  return (
    <span className="a-estimate-label" title={t("estimate.hint")}>
      {t(historical ? "estimate.historical" : "estimate.label")}
      {scenario ? ` · ${scenario === "both" ? `${t("scenario.moderate")} / ${t("scenario.fast")}` : t(`scenario.${scenario}`)}` : null}
    </span>
  );
}
