import { asyncView } from "@/lib/next-compat/async-view";
import Form from "@/lib/next-compat/form";
import Link from "@/lib/next-compat/link";
import { getTranslations } from "@/lib/next-compat/intl";

import { ErrorState } from "@/components/ErrorState";
import { MetaBar, PageHeader } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { fetchJobBoard } from "../api";
import { OpeningItem } from "./OpeningItem";

type Mode = "onsite" | "hybrid" | "remote";

/** Live openings in Malaysia (and remote roles open to Malaysians), for the roles Adept plans. */
async function JobBoardViewAsync({
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
  const total = d.roles.reduce((n, r) => n + r.open_count, 0);
  return (
    <div className="a-view">
      <PageHeader
        title={t("board.title")}
        description={t("board.description", { count: total, roles: d.roles.length, date: d.fetched_on ?? d.meta.snapshot_date })}
      >
        <MetaBar meta={d.meta} />
      </PageHeader>

      <Form action="/app/jobs" className="a-card a-controls a-jobfilters">
        <input type="hidden" name="scenario" value={scenario} />
        <label className="a-field">
          {t("board.role")}
          <select className="a-select" name="role" defaultValue={roleId ?? ""}>
            <option value="">{t("board.allRoles")}</option>
            {d.roles.map((r) => (
              <option key={r.role_id} value={r.role_id}>
                {r.role_label} ({r.open_count})
              </option>
            ))}
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
              <OpeningItem key={o.id} o={o} showFit={Boolean(roleId)} />
            ))}
          </ul>
        ) : (
          <p className="a-muted">{t("board.empty")}</p>
        )}
        {pages > 1 ? (
          <nav className="a-pager" aria-label={t("board.pages")}>
            {d.page > 1 ? <Link href={href(d.page - 1)}>← {t("board.prev")}</Link> : <span />}
            <span className="a-small a-muted">{t("board.page", { page: d.page, pages })}</span>
            {d.page < pages ? <Link href={href(d.page + 1)}>{t("board.next")} →</Link> : <span />}
          </nav>
        ) : null}
        {roleId ? null : <p className="a-small a-muted">{t("board.pickRole")}</p>}
      </section>
    </div>
  );
}

export const JobBoardView = asyncView(JobBoardViewAsync);
