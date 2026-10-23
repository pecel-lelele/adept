import { asyncView } from "@/lib/next-compat/async-view";
import { getTranslations } from "@/lib/next-compat/intl";

import { ApiError, Card, CardContent, PageHeader, SourceBadge } from "@/components";

import { fetchDataFreshness } from "../api";

/** Admin pages for trend sources and snapshot versions (F2 Final). */
async function AdminDataViewAsync({ view }: { view: "sources" | "snapshots" }) {
  const t = await getTranslations("trends");
  const result = await fetchDataFreshness();
  return (
    <section>
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

export const AdminDataView = asyncView(AdminDataViewAsync);
