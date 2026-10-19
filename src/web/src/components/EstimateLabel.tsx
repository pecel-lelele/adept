import { useTranslations } from "next-intl";

import type { ScenarioId } from "@/lib/api";

import { Badge } from "./ui/badge";

/** Every prediction is labelled as an estimate, with its scenario. */
export function EstimateLabel({ scenario, isEstimate = true }: { scenario?: ScenarioId; isEstimate?: boolean }) {
  const t = useTranslations("common");
  if (!isEstimate) return null;
  return (
    <Badge variant="warning" title={t("estimate.hint")}>
      {t("estimate.label")}
      {scenario ? ` · ${t(`scenario.${scenario}`)}` : null}
    </Badge>
  );
}
