import type { RecommendationMeta } from "@/lib/api";

import { EstimateLabel } from "./EstimateLabel";
import { SourceBadge } from "./SourceBadge";

/** Renders the output contract (sources, date, scenario, estimate) of a response. */
export function MetaBar({ meta }: { meta: RecommendationMeta }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <EstimateLabel scenario={meta.scenario} isEstimate={meta.is_estimate} />
      <SourceBadge sources={meta.sources} snapshotDate={meta.snapshot_date} />
    </div>
  );
}
