import { useTranslations } from "next-intl";

import type { RecommendationMeta } from "@/lib/api";

/**
 * Forecasts stay identifiable as estimates without a visible chip: the cue is announced to
 * screen readers and shown as a tooltip on the wrapping element where one is given.
 */
export function EstimateLabel({ isEstimate = true }: { scenario?: RecommendationMeta["scenario"]; isEstimate?: boolean; historical?: boolean }) {
  const t = useTranslations("common");
  if (!isEstimate) return null;
  return <span className="a-sr">{t("estimate.label")}. {t("estimate.hint")}</span>;
}
