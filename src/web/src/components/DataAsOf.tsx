import { getTranslations } from "next-intl/server";

import { fetchDataSources, type DataSourceId } from "@/lib/data-sources";
import type { Schemas } from "@/lib/api";

/** Source dates describe the observed data; a later snapshot or sync cannot refresh them. */
export async function DataAsOf({ source, meta }: { source: DataSourceId; meta?: Schemas["RecommendationMeta"] }) {
  const result = await fetchDataSources();
  const item = result.ok ? result.data.sources.find((s) => s.source === source) : undefined;
  // A selected snapshot already carries dated sources: keep them visible when the optional
  // global freshness service is unavailable, without borrowing a different snapshot's date.
  const day = meta?.observed_to ?? meta?.snapshot_date ?? item?.data_as_of ?? item?.last_fetched_at;
  if (!day) return null;
  const t = await getTranslations("trends.dataSources");
  const snapshotDate = meta?.snapshot_date ?? item?.snapshot_date;
  const historical = day && snapshotDate && Date.parse(snapshotDate) - Date.parse(day) > 60 * 864e5;
  const fallback = meta?.is_fallback ?? item?.is_fallback;
  return (
    <p className="a-muted a-small" data-source={source}>
      {t(fallback ? "asOfFrozen" : "asOf", { date: day })} · {meta?.sources.map((s) => s.name).join(" · ") || item?.source_name}
      {item?.is_stale || historical || fallback ? ` · ${t("lastGood", { date: day })}` : ""}
      {item?.last_checked_at ? ` · ${t("lastChecked", { time: item.last_checked_at })}` : ""}
      {historical || (!meta && item?.is_historical_replay) ? ` · ${t("historicalReplay", { date: snapshotDate ?? "" })}` : ""}
    </p>
  );
}
