"use client";

import { useFormatter, useTranslations } from "next-intl";
import type { Schemas } from "@/lib/api";
import type { DataSourceFreshness } from "@/lib/data-sources";
import { RefreshDataButton } from "./RefreshDataButton";

export function DataSourcesPanel({ sources, history }: { sources: DataSourceFreshness[]; history?: Schemas["RefreshHistory"] }) {
  const t = useTranslations("trends.dataSources");
  const progress = useTranslations("trends.refreshUser.states");
  const format = useFormatter();
  const time = (value: string) => format.dateTime(new Date(value), { dateStyle: "medium", timeStyle: "short" });
  const trend = sources.find((source) => source.source === "trends");
  return (
    <div className="space-y-3">
      <h2>{t("title")}</h2>
      <p className="a-muted a-small">{t("help")}</p>
      <RefreshDataButton dataAsOf={trend?.data_as_of ?? trend?.last_fetched_at ?? undefined} />
      {history ? <p className="a-small">{t("nextScheduled", { time: time(history.next_scheduled_at) })}</p> : null}
      <ul className="space-y-3">
        {sources.map((source) => (
          <li key={source.source} className="space-y-1 border-t pt-3 text-sm" data-source={source.source}>
            <strong>{t(`labels.${source.source}`)}</strong>
            <p>{source.data_as_of || source.last_fetched_at ? t("asOf", { date: source.data_as_of ?? source.last_fetched_at ?? "" }) : t("noDate")} · {t("rows", { count: source.rows })}</p>
            <p className="a-muted">{t(source.served_from === "database" ? "fromDatabase" : "fromSeed")}</p>
            {source.is_fallback ? <p className="a-small">{t("fallback")}</p> : null}
            {source.is_historical_replay ? <p className="a-small">{t("historicalReplay", { date: source.snapshot_date ?? "" })}</p> : null}
          </li>
        ))}
      </ul>
      {history?.runs.length ? <div><h3>{t("recentRuns")}</h3><ul>
        {history.runs.map((run) => <li key={run.run_id}>{time(run.started_at)} · {progress(run.status === "ok" ? "done" : run.status === "failed" ? "failed" : run.status === "queued" ? "pending" : "running")}</li>)}
      </ul></div> : null}
    </div>
  );
}
