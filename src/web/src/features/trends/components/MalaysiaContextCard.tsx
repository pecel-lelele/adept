import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { call, getApi } from "@/lib/api";

/** National survey context is stored data; it is never presented as a role forecast. */
export async function MalaysiaContextCard() {
  const t = await getTranslations("trends.nationalContext");
  const api = await getApi();
  const result = await call(api.GET("/api/v1/trends/malaysia-context"));
  if (!result.ok) return null;
  const data = result.data;
  return <details className="a-card a-disclosure">
    <summary>{t("title", { month: data.observed_month.slice(0, 7) })}</summary>
    <p>{t("description")}</p>
    <dl className="a-facts">
      <div><dt>{t("unemployment")}</dt><dd>{data.unemployment_rate}%</dd></div>
      <div><dt>{t("participation")}</dt><dd>{data.participation_rate}%</dd></div>
      <div><dt>{t("employmentRatio")}</dt><dd>{data.employment_population_ratio}%</dd></div>
    </dl>
    <MetaBar meta={data.meta} />
  </details>;
}
