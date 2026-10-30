"use client";

import { RefreshCw } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, useTransition } from "react";

import {
  rescoreTrends,
  startTrendRefresh,
  trendRefreshStatus,
  type Outcome,
  type RefreshStatus,
  type RescoreResult,
} from "../refresh-actions";

const POLL_MS = 10000;
// The workflow's own job limit is 30 minutes; stop polling a little after it.
const POLL_LIMIT_MS = 35 * 60 * 1000;

type Failure = Extract<Outcome<unknown>, { ok: false }>;

/** Admin: fetch the latest trend data (GitHub workflow) or re-score stored signals. */
export function TrendRefreshPanel() {
  const resultsHref = usePathname().startsWith("/org") ? "/org/radar" : "/app/matches";
  const t = useTranslations("trends.refresh");
  const router = useRouter();
  const [run, setRun] = useState<RefreshStatus | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [rescore, setRescore] = useState<RescoreResult | null>(null);
  const [pending, start] = useTransition();
  const [pollTick, setPollTick] = useState(0);
  const startedAt = useRef(0);
  const refreshed = useRef<number | null>(null);

  const active = run !== null && run.status !== "completed";

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      if (Date.now() - startedAt.current > POLL_LIMIT_MS) {
        setFailure({ ok: false, status: 0, code: "poll_timeout" });
        setRun(null);
        return;
      }
      const result = await trendRefreshStatus(run?.run_id ?? null);
      if (cancelled) return;
      if (result.ok) setRun(result.data);
      else setFailure(result);
      setPollTick((n) => n + 1);
    }, POLL_MS);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [active, run, pollTick]);

  useEffect(() => {
    // Re-render server data (snapshot date, sources) once per successful run.
    if (run?.caches_cleared && run.run_id != null && refreshed.current !== run.run_id) {
      refreshed.current = run.run_id;
      router.refresh();
    }
  }, [run, router]);

  const fetchLatest = () => start(async () => {
    setFailure(null);
    setRescore(null);
    startedAt.current = Date.now();
    const result = await startTrendRefresh();
    if (result.ok) setRun(result.data);
    else setFailure(result);
  });

  const rescoreNow = () => start(async () => {
    setFailure(null);
    const result = await rescoreTrends();
    if (result.ok) {
      setRescore(result.data);
      if (result.data.status === "published") router.refresh();
    } else setFailure(result);
  });

  const stage = run === null ? null
    : run.status !== "completed" ? t(run.status === "queued" ? "queued" : "inProgress")
      : run.conclusion === "success" ? t("succeeded") : t("failed", { conclusion: run.conclusion ?? "unknown" });

  return (
    <div className="space-y-3">
      <h2>{t("title")}</h2>
      <p className="a-muted a-small">{t("help")}</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="a-btn" disabled={pending || active} onClick={fetchLatest}>
          <RefreshCw size={14} aria-hidden /> {t("fetch")}
        </button>
        <button type="button" className="a-btn is-ghost" disabled={pending || active} onClick={rescoreNow}>
          {t("rescore")}
        </button>
      </div>
      <div role="status" aria-live="polite" className="space-y-1 text-sm">
        {pending ? <p>{t("working")}</p> : null}
        {run?.already_running ? <p>{t("alreadyRunning")}</p> : null}
        {stage ? <p>{stage}</p> : null}
        {run?.run_url ? <p><a href={run.run_url} target="_blank" rel="noreferrer">{t("viewRun")}</a></p> : null}
        {run?.status === "completed" && run.conclusion === "success" && run.snapshot_date ? (
          <p>
            {t("newSnapshot", { date: run.snapshot_date })}{" "}
            <Link href={resultsHref}>{t("openMatches")}</Link>
          </p>
        ) : null}
        {run?.status === "completed" && run.conclusion !== "success" ? <p>{t("lastGoodStays")}</p> : null}
        {rescore ? (
          <p>
            {t(`rescore_${rescore.status}`, { date: rescore.snapshot_date ?? "—" })}
            {rescore.status === "published" ? <> <Link href={resultsHref}>{t("openMatches")}</Link></> : null}
          </p>
        ) : null}
        {failure ? (
          <p className="a-notice">
            {failure.code === "refresh_not_configured" ? t("notConfigured")
              : failure.code === "refresh_in_progress" ? t("alreadyRunning")
                : failure.code === "forbidden" ? t("forbidden")
                  : failure.code === "poll_timeout" ? t("pollTimeout")
                    : t("error", { code: failure.code })}
          </p>
        ) : null}
      </div>
    </div>
  );
}
