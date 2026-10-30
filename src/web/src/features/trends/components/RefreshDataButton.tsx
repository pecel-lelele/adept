"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { checkRefresh, pollRefresh, type RefreshRun } from "../refresh-actions";

export type RefreshPhase = "idle" | "checking" | "up_to_date" | "running" | "done" | "failed" | "cooldown";
export type RefreshView = {
  phase: RefreshPhase;
  run?: RefreshRun;
  elapsed: number;
  retryAt?: string;
  dataAsOf?: string;
  checkedAt?: number;
};

export function RefreshProgressView({ state, onRefresh }: { state: RefreshView; onRefresh: () => void }) {
  const t = useTranslations("trends.refreshUser");
  const day = state.run?.data_as_of ?? state.dataAsOf ?? t("unknownDate");
  const busy = state.phase === "checking" || state.phase === "running";
  const retry = state.run?.retry_at ?? state.retryAt;
  const minutes = retry && state.checkedAt ? Math.max(1, Math.ceil((Date.parse(retry) - state.checkedAt) / 60000)) : 1;
  return (
    <section className="a-refresh" aria-label={t("title")} data-refresh-state={state.phase}>
      <button type="button" className="a-btn is-ghost" disabled={busy} onClick={onRefresh}>
        {busy && (state.phase === "checking" || state.elapsed < 1) ? <span className="a-refresh-spinner" aria-hidden="true" /> : null}
        {state.phase === "checking" ? t("checking") : state.phase === "running" ? t("refreshing") : state.phase === "failed" ? t("retry") : t("title")}
      </button>
      <div role="status" aria-live="polite" aria-atomic="true" className="a-small a-muted">
        {state.phase === "checking" ? <span className="a-sr">{t("checking")}</span> : null}
        {state.phase === "up_to_date" ? <p>{t("latest", { date: day })}</p> : null}
        {state.phase === "done" ? <p>{t("done", { date: day })}</p> : null}
        {state.phase === "failed" ? <p>{t("failed", { date: day })}</p> : null}
        {state.phase === "cooldown" ? <p>{t("cooldown", { minutes })}</p> : null}
        {state.phase === "running" ? <p>{t(state.run?.shared ? "shared" : "refreshing")}</p> : null}
      </div>
      {state.phase === "running" && state.elapsed >= 1 ? (
        <div className="a-card a-refresh-panel" aria-busy="true">
          <p className="a-small">{t("elapsed", { seconds: state.elapsed })}</p>
          <ol className="a-refresh-steps">
            {state.run?.steps?.map((step) => (
              <li key={step.source} data-status={step.status}>
                <strong>{t(`sources.${step.source}`)}</strong>
                <span>{t(`states.${step.status}`)}</span>
              </li>
            ))}
          </ol>
          {state.elapsed >= 15 ? <p className="a-small a-muted">{t("warmup")}</p> : null}
          <p className="a-small a-muted">{t("keepShowing", { date: day })}</p>
        </div>
      ) : null}
    </section>
  );
}

export function RefreshDataButton({ dataAsOf }: { dataAsOf?: string }) {
  const router = useRouter();
  const [state, setState] = useState<RefreshView>({ phase: "idle", elapsed: 0, dataAsOf });
  const [visible, setVisible] = useState(true);
  const [, transition] = useTransition();
  const attempt = useRef(0);
  const completed = useRef<string | null>(null);
  const receive = useCallback((run: RefreshRun) => {
    const phase: RefreshPhase = run.status === "ok" ? "done" : run.status === "failed" ? "failed" : run.status === "up_to_date" ? "up_to_date" : run.status === "cooldown" ? "cooldown" : "running";
    setState((previous) => ({ ...previous, run, phase, checkedAt: Date.now(), elapsed: Math.max(0, Math.floor((Date.now() - Date.parse(run.started_at)) / 1000)) }));
    if ((phase === "done" || phase === "failed") && run.run_id && completed.current !== run.run_id) {
      completed.current = run.run_id ?? null;
      transition(() => router.refresh());
    }
  }, [router]);
  const refresh = async () => {
    setState((previous) => ({ phase: "checking", elapsed: 0, dataAsOf: previous.run?.data_as_of ?? previous.dataAsOf }));
    attempt.current = 0;
    const result = await checkRefresh();
    if (result.ok) receive(result.data);
    else setState((previous) => ({ ...previous, phase: result.retryAt ? "cooldown" : "failed", retryAt: result.retryAt, checkedAt: Date.now() }));
  };
  useEffect(() => {
    const update = () => setVisible(document.visibilityState !== "hidden");
    update();
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  useEffect(() => {
    if (state.phase !== "running" || !state.run?.run_id || !visible) return;
    let cancelled = false;
    const runId = state.run.run_id;
    const timeout = setTimeout(async () => {
      const result = await pollRefresh(runId);
      if (cancelled) return;
      attempt.current += 1;
      if (result.ok) receive(result.data);
      else setState((previous) => ({ ...previous, phase: "failed" }));
    }, [1000, 2000, 5000][Math.min(attempt.current, 2)]);
    return () => { cancelled = true; clearTimeout(timeout); };
  }, [state.phase, state.run, visible, receive]);
  useEffect(() => {
    if (state.phase !== "running" && state.phase !== "cooldown") return;
    const timer = setInterval(() => setState((previous) => {
      const checkedAt = Date.now();
      const retry = previous.run?.retry_at ?? previous.retryAt;
      return { ...previous, checkedAt, elapsed: previous.elapsed + 1, phase: previous.phase === "cooldown" && retry && checkedAt >= Date.parse(retry) ? "idle" : previous.phase };
    }), 1000);
    return () => clearInterval(timer);
  }, [state.phase]);
  return <RefreshProgressView state={state} onRefresh={refresh} />;
}
