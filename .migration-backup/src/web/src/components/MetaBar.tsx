import type { RecommendationMeta } from "@/lib/api";
import { useTranslations } from "next-intl";

import { EstimateLabel } from "./EstimateLabel";
import { SourceBadge } from "./SourceBadge";

/**
 * The output contract of a response (estimate label, snapshot date, measured period, sources),
 * collapsed to one line that opens to the full citation.
 */
export function MetaBar({ meta }: { meta: RecommendationMeta }) {
  const t = useTranslations("common.design");
  const parts = [
    meta.snapshot_date,
    meta.observed_from && meta.observed_to ? t("observed", { from: meta.observed_from, to: meta.observed_to }) : null,
    t("evidence"),
  ].filter(Boolean);
  return (
    <details className="a-metabar">
      <summary>
        {meta.is_estimate ? (
          <>
            <EstimateLabel scenario={meta.scenario} isEstimate /> ·{" "}
          </>
        ) : null}
        {parts.join(" · ")}
      </summary>
      <div className="a-metabar-body">
        <EstimateLabel scenario={meta.scenario} isEstimate={meta.is_estimate} />
        <SourceBadge sources={meta.sources} snapshotDate={meta.snapshot_date} />
      </div>
    </details>
  );
}
