import type { RecommendationMeta } from "@/lib/api";
import { useTranslations } from "next-intl";

import { EstimateLabel } from "./EstimateLabel";
import { SourceBadge } from "./SourceBadge";
import { TrendProvenanceNotice } from "./TrendProvenanceNotice";

/**
 * The output contract of a response (estimate label, snapshot date, measured period, sources),
 * collapsed to one line that opens to the full citation.
 */
export function MetaBar({ meta }: { meta: RecommendationMeta & Parameters<typeof TrendProvenanceNotice>[0]["meta"] & { data_provenance_note?: string | null } }) {
  const t = useTranslations("common.design");
  const tf = useTranslations("common.freshness");
  const observedTo = meta.observation_window_end ?? meta.observed_to;
  const historical = meta.is_replay === true || Boolean(observedTo && Date.parse(meta.snapshot_date) - Date.parse(observedTo) > 60 * 864e5);
  const parts = [
    tf("snapshot", { date: meta.snapshot_date }),
    meta.sources.map((source) => source.name).join(", "),
    t("evidence"),
  ].filter(Boolean);
  return (
    <>
      <details className="a-metabar">
        <summary>
          {meta.is_estimate ? (
            <>
              <EstimateLabel scenario={meta.scenario} isEstimate historical={historical} /> ·{" "}
            </>
          ) : null}
          {!meta.is_estimate && historical ? <span data-trend-replay="true">{tf("historicalData")} · </span> : null}
          {meta.is_replay === null ? <span>{tf("unverifiedShort")} · </span> : null}
          {meta.is_fallback ? <span role="status">{tf("fallbackShort")} · </span> : null}
          {parts.join(" · ")}
        </summary>
        <div className="a-metabar-body">
          <TrendProvenanceNotice meta={meta} />
          {meta.is_fallback ? <p>{tf("fallback", { date: meta.snapshot_date })}</p> : null}
          {meta.observed_from && meta.observed_to ? <p>{t("observed", { from: meta.observed_from, to: meta.observed_to })}</p> : null}
          {meta.data_provenance_note ? <p>{meta.data_provenance_note}</p> : null}
          <EstimateLabel scenario={meta.scenario} isEstimate={meta.is_estimate} />
          <SourceBadge sources={meta.sources} snapshotDate={observedTo ?? meta.snapshot_date} />
        </div>
      </details>
    </>
  );
}
