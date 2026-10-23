import { asyncView } from "@/lib/next-compat/async-view";
import { getTranslations } from "@/lib/next-compat/intl";

import { call, getApi } from "@/lib/api";

import { Badge } from "./ui/badge";

/** "Trend data as of <date>" from GET /meta/data-freshness. */
async function DataFreshnessBadgeAsync() {
  const t = await getTranslations("common.freshness");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/meta/data-freshness"));
  if (!result.ok) return <Badge variant="danger">{t("unavailable")}</Badge>;
  const { snapshot_date, sources } = result.data;
  return (
    <Badge variant="secondary" title={sources.map((s) => s.name).join(", ")}>
      {t("label", { date: snapshot_date })} · {sources.map((s) => s.name).join(", ")}
    </Badge>
  );
}

export const DataFreshnessBadge = asyncView(DataFreshnessBadgeAsync);
