import { ChevronLeft, ChevronRight } from "lucide-react";
import Form from "next/form";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchJobBoard } from "../api";
import { OpeningItem, placeCounts } from "./OpeningItem";

type Mode = "onsite" | "hybrid" | "remote";

/** Live openings in Malaysia (and remote roles open to Malaysians), for the roles Adept plans. */
export async function JobBoardView({
  scenario,
  roleId,
  q,
  workMode,
  page = 1,
}: {
  scenario: ScenarioId;
  roleId?: string;
  q?: string;
  workMode?: Mode;
  page?: number;
}) {
  const t = await getTranslations("jobs");
  const result = await fetchJobBoard(scenario, { roleId, q, workMode, page });
  if (!result.ok) return <ErrorState failure={result} />;
  const d = result.data;
  const pages = Math.max(1, Math.ceil(d.total / d.page_size));
  const href = (p: number) => {
    const s = new URLSearchParams({ scenario, page: String(p) });
    if (roleId) s.set("role", roleId);
    if (q) s.set("q", q);
    if (workMode) s.set("mode", workMode);
    return `/app/jobs?${s.toString()}`;
  };
  return (
    <div className="a-view">
      <PageHeader title={t("board.title")} description={await placeCounts(d.places)} />

      <Form action="/app/jobs" className="a-card a-controls a-jobfilters">
        <input type="hidden" name="scenario" value={scenario} />
        <label className="a-field">
          {t("board.role")}
          <select className="a-select" name="role" defaultValue={roleId ?? ""}>
            <option value="">{t("board.allRoles")}</option>
            {d.roles.map((r) => {
              const remote = r.places.remote_explicit_my + r.places.remote_assumed_worldwide;
              return (
                <option key={r.role_id} value={r.role_id}>
                  {r.role_label} ({remote ? t("board.roleSplit", { inMalaysia: r.places.in_malaysia, remote }) : r.places.in_malaysia})
                </option>
              );
            })}
          </select>
        </label>
        <label className="a-field">
          {t("board.where")}
          <select className="a-select" name="mode" defaultValue={workMode ?? ""}>
            <option value="">{t("board.anyMode")}</option>
            <option value="onsite">{t("board.onsite")}</option>
            <option value="hybrid">{t("hybrid")}</option>
            <option value="remote">{t("board.remoteOnly")}</option>
          </select>
        </label>
        <label className="a-field">
          {t("board.search")}
          <input className="a-input" name="q" defaultValue={q ?? ""} placeholder={t("board.searchHint")} maxLength={80} />
        </label>
        <button className="a-btn" type="submit">
          {t("board.apply")}
        </button>
      </Form>

      <section className="a-card" aria-labelledby="h-board">
        <div className="a-card-head">
          <h2 id="h-board">{t("board.results", { count: d.total })}</h2>
        </div>
        {d.openings.length ? (
          <ul className="a-jobs">
            {d.openings.map((o) => (
              <OpeningItem key={o.id} o={o} showFit={Boolean(roleId)} malaysiaFocus />
            ))}
          </ul>
        ) : (
          <p className="a-muted">{t("board.empty")}</p>
        )}
        {pages > 1 ? (
          <nav className="a-pager" aria-label={t("board.pages")}>
            {d.page > 1 ? <Link href={href(d.page - 1)}><ChevronLeft size={16} aria-hidden />{t("board.prev")}</Link> : <span className="a-pager-disabled" aria-disabled="true"><ChevronLeft size={16} aria-hidden />{t("board.prev")}</span>}
            <span className="a-pager-current" aria-live="polite">{t("board.page", { page: d.page, pages })}</span>
            {d.page < pages ? <Link href={href(d.page + 1)}>{t("board.next")}<ChevronRight size={16} aria-hidden /></Link> : <span className="a-pager-disabled" aria-disabled="true">{t("board.next")}<ChevronRight size={16} aria-hidden /></span>}
          </nav>
        ) : null}
        {roleId ? null : <p className="a-small a-muted">{t("board.pickRole")}</p>}
      </section>
    </div>
  );
}
