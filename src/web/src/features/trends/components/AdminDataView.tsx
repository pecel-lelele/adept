import { getTranslations } from "next-intl/server";

import { ApiError, Card, CardContent, PageHeader, SourceBadge, StubBanner } from "@/components";

import { fetchDataFreshness } from "../api";

/** Admin pages for trend sources and snapshot versions (F2 Final). */
export async function AdminDataView({ view }: { view: "sources" | "snapshots" }) {
  const t = await getTranslations("trends");
  const result = await fetchDataFreshness();
  return (
    <section>
      <StubBanner feature="F2 admin data pages" endpoint="GET /api/v1/meta/data-freshness" />
      <PageHeader title={view === "sources" ? t("sourcesTitle") : t("snapshotsTitle")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <Card>
          <CardContent className="space-y-2 pt-4">
            <p className="text-sm">{t("snapshotDate", { date: result.data.snapshot_date })}</p>
            <SourceBadge sources={result.data.sources} snapshotDate={result.data.snapshot_date} />
          </CardContent>
        </Card>
      )}
    </section>
  );
}
