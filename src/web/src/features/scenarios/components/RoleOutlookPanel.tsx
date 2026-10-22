import { getTranslations } from "next-intl/server";

import { ApiError, EstimateLabel, SourceBadge } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchOutlook } from "../api";

/**
 * Outlook for one role under each scenario, with its low/high range (F3). With a snapshot date
 * the outlook uses only the snapshots up to that date, so it matches a historical match page.
 */
export async function RoleOutlookPanel({
  roleId,
  scenario,
  snapshotDate,
}: {
  roleId: string;
  scenario: ScenarioId;
  snapshotDate?: string;
}) {
  const t = await getTranslations("scenarios");
  const tc = await getTranslations("common.scenario");
  const result = await fetchOutlook(roleId, snapshotDate);
  if (!result.ok) return <ApiError message={result.message} />;
  const all = result.data.outlooks;
  const top = Math.max(1.5, ...all.map((o) => o.high));
  const pos = (v: number) => `${Math.max(0, Math.min(100, (v / top) * 100))}%`;
  return (
    <div className="a-outlook">
      {all.map((o) => (
        <div key={o.scenario} className="a-outlook-row" data-current={o.scenario === scenario || undefined}>
          <span className="a-outlook-name">{tc(o.scenario)}</span>
          <span className="a-outlook-track" aria-hidden>
            <i className="a-outlook-range" style={{ left: pos(o.low), width: `calc(${pos(o.high)} - ${pos(o.low)})` }} />
            <i className="a-outlook-base" style={{ left: pos(1) }} />
            <b style={{ left: pos(o.outlook) }} />
          </span>
          <span className="a-outlook-value">
            {o.outlook.toFixed(2)}
            <small>{t("range", { low: o.low.toFixed(2), high: o.high.toFixed(2) })}</small>
          </span>
        </div>
      ))}
      <div className="a-chips">
        <EstimateLabel isEstimate={result.data.meta.is_estimate} />
        <SourceBadge sources={result.data.meta.sources} snapshotDate={result.data.meta.snapshot_date} />
      </div>
    </div>
  );
}
