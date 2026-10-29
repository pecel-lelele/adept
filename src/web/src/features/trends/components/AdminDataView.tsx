import { getTranslations } from "next-intl/server";

import { ApiError, Card, CardContent, PageHeader, SourceBadge } from "@/components";

import { fetchDataFreshness } from "../api";

/** Admin pages for trend sources and snapshot versions (F2 Final). */
export async function AdminDataView({ view }: { view: "sources" | "snapshots" }) {
  const t = await getTranslations("trends");
  const tf = await getTranslations("common.freshness");
  const result = await fetchDataFreshness();
  return (
    <section>
      <PageHeader title={view === "sources" ? t("sourcesTitle") : t("snapshotsTitle")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <Card>
          <CardContent className="space-y-2 pt-4">
            {result.data.is_fallback ? <p className="a-notice" role="status">{tf("fallback", { date: result.data.snapshot_date })}</p> : null}
            <p className="text-sm">{t("snapshotDate", { date: result.data.snapshot_date })}</p>
            <SourceBadge sources={result.data.sources} snapshotDate={result.data.snapshot_date} />
          </CardContent>
        </Card>
      )}
    </section>
  );
}
