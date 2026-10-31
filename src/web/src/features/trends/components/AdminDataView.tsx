import { getTranslations } from "next-intl/server";

import { Card, CardContent, ErrorState, PageHeader, SourceBadge } from "@/components";

import { fetchDataSources, fetchRecentRefreshes } from "@/lib/data-sources";

import { fetchDataFreshness } from "../api";
import { DataSourcesPanel } from "./DataSourcesPanel";

/** Admin pages for trend sources and snapshot versions (F2 Final). */
export async function AdminDataView({ view }: { view: "sources" | "snapshots" }) {
  const t = await getTranslations("trends");
  const tf = await getTranslations("common.freshness");
  const result = await fetchDataFreshness();
  const sources = view === "snapshots" ? await fetchDataSources() : null;
  const history = view === "snapshots" ? await fetchRecentRefreshes() : null;
  return (
    <section>
      <PageHeader title={view === "sources" ? t("sourcesTitle") : t("snapshotsTitle")} />
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <Card>
          <CardContent className="space-y-2 pt-4">
            {result.data.is_fallback ? <p className="a-notice" role="status">{tf("fallback", { date: result.data.snapshot_date })}</p> : null}
            <p className="text-sm">{t("snapshotDate", { date: result.data.snapshot_date })}</p>
            <SourceBadge sources={result.data.sources} snapshotDate={result.data.snapshot_date} />
          </CardContent>
        </Card>
      )}
      {sources?.ok ? (
        <Card className="mt-4">
          <CardContent className="pt-4">
            <DataSourcesPanel sources={sources.data.sources} history={history?.ok ? history.data : undefined} />
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}
