import { getTranslations } from "next-intl/server";

import { call, getApi } from "@/lib/api";

import { Badge } from "./ui/badge";
import { TrendProvenanceNotice } from "./TrendProvenanceNotice";

/** "Trend data as of <date>" from GET /meta/data-freshness. */
export async function DataFreshnessBadge() {
  const t = await getTranslations("common.freshness");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/meta/data-freshness"));
  if (!result.ok) return <Badge variant="danger">{t("unavailable")}</Badge>;
  const { snapshot_date, sources, is_fallback } = result.data;
  return (
    <div>
    <TrendProvenanceNotice meta={result.data} />
    <Badge variant="secondary" title={sources.map((s) => s.name).join(", ")}>
      {t(result.data.is_replay === true ? "historical" : result.data.is_replay === null ? "unverified" : is_fallback ? "fallback" : "label", { date: snapshot_date })} · {sources.map((s) => s.name).join(", ")}
    </Badge>
    </div>
  );
}
