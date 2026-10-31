"use client";

import { useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { MetaBar } from "@/components/MetaBar";
import type { Schemas } from "@/lib/api";

type Observation = Schemas["MalaysiaLabourContext"];

/** Month selector and three observed survey rates, kept separate from forecast scores. */
export function MalaysiaContextPanel({ observations }: { observations: Observation[] }) {
  const t = useTranslations("trends.nationalContext");
  const locale = useLocale();
  const headingId = useId();
  const [month, setMonth] = useState(observations[0]?.observed_month ?? "");
  const data = observations.find((item) => item.observed_month === month) ?? observations[0];
  if (!data) return null;
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const stats = [
    { key: "unemployment", value: data.unemployment_rate },
    { key: "participation", value: data.participation_rate },
    { key: "employmentRatio", value: data.employment_population_ratio },
  ] as const;
  return (
    <section className="a-card a-pad labour-context" aria-labelledby={headingId}>
      <header className="labour-heading">
        <div><h2 id={headingId}>{t("heading")}</h2><p>{t("description")}</p></div>
        <div className="labour-month">
          <label>{t("month")}
            <select aria-label={t("month")} aria-describedby={observations.length < 2 ? `${headingId}-month-help` : undefined}
              value={data.observed_month} onChange={(event) => setMonth(event.target.value)} disabled={observations.length < 2}>
              {observations.map((item) => <option key={item.observed_month} value={item.observed_month}>{item.observed_month.slice(0, 7)}</option>)}
            </select>
          </label>
          {observations.length < 2 ? <small id={`${headingId}-month-help`}>{t("singleMonth")}</small> : null}
        </div>
      </header>
      <dl className="labour-stats">
        {stats.map(({ key, value }) => (
          <div className="labour-stat" key={key}>
            <dt>{t(key)}</dt><dd>{number.format(value)}<span>%</span></dd>
            <span className="labour-stat-track" aria-hidden><i style={{ width: `${value}%` }} /></span>
          </div>
        ))}
      </dl>
      <MetaBar meta={data.meta} />
    </section>
  );
}
