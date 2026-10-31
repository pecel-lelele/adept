"use client";

import { Clock3 } from "lucide-react";
import { useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { EstimateLabel } from "@/components/EstimateLabel";
import type { Schemas } from "@/lib/api";

type Observation = Schemas["MalaysiaLabourContext"];

export function MalaysiaContextPanel({ observations }: { observations: Observation[] }) {
  const t = useTranslations("trends.nationalContext");
  const freshness = useTranslations("common.freshness");
  const design = useTranslations("common.design");
  const locale = useLocale();
  const headingId = useId();
  const [month, setMonth] = useState(observations[0]?.observed_month ?? "");
  const data = observations.find((item) => item.observed_month === month) ?? observations[0];
  if (!data) return null;
  const { meta } = data;
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const providers = [...new Set(meta.sources.map((source) => source.name.split(":")[0]))].join(" · ");
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
      {meta.is_fallback ? <p className="labour-snapshot" role="status"><Clock3 size={13} aria-hidden />{freshness("fallback", { date: meta.snapshot_date })}</p> : null}
      {meta.is_estimate ? <EstimateLabel scenario={meta.scenario} /> : null}
      <dl className="labour-stats">
        {stats.map(({ key, value }) => (
          <div className="labour-stat" key={key}>
            <dt>{t(key)}</dt><dd>{number.format(value)}<span>%</span></dd>
            <span className="labour-stat-track" aria-hidden><i style={{ width: `${value}%` }} /></span>
          </div>
        ))}
      </dl>
      <footer className="labour-footer">
        <span>{providers} · {t("asOf", { date: meta.snapshot_date })}</span>
        <details className="labour-sources" key={data.observed_month}>
          <summary>{design("evidence")}</summary>
          <div>
            {meta.observed_from && meta.observed_to ? <p>{design("observed", { from: meta.observed_from, to: meta.observed_to })}</p> : null}
            <ul>{meta.sources.map((source) => <li key={`${source.name}:${source.url}`}>
              {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> : source.name}
              <span>{t("retrieved", { date: source.retrieved_at })}</span>
            </li>)}</ul>
          </div>
        </details>
      </footer>
    </section>
  );
}
