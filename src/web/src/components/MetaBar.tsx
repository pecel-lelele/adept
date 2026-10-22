import type { RecommendationMeta } from "@/lib/api";
import { useTranslations } from "next-intl";

import { EstimateLabel } from "./EstimateLabel";
import { SourceBadge } from "./SourceBadge";

/** Renders the output contract (sources, date, scenario, estimate) of a response. */
export function MetaBar({ meta }: { meta: RecommendationMeta }) {
  const t = useTranslations("common.design");
  return (
    <details className="meta-disclosure">
      <summary><EstimateLabel scenario={meta.scenario} isEstimate={meta.is_estimate} /> · {meta.snapshot_date} · {t("evidence")}</summary>
      <div className="flex flex-wrap items-center gap-2">
      <EstimateLabel scenario={meta.scenario} isEstimate={meta.is_estimate} />
      <SourceBadge sources={meta.sources} snapshotDate={meta.snapshot_date} />
      </div>
    </details>
  );
}
