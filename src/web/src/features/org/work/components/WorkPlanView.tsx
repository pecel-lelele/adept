import { ArrowUpRight, Building2, CalendarDays, Clock3, Wallet } from "lucide-react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { EmptyState, ErrorState, MetaBar, PageHeader } from "@/components";
import { AssignedPackageView } from "@/features/org/components/AssignedPackageView";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import type { WorkspaceOption } from "@/lib/auth/workspaces";

import { decideProgrammeAction } from "../actions";
import { type Assignment, byStatus, fetchMyProgrammes } from "../api";

const REASONS = ["already_have_skill", "pace", "language", "accessibility", "schedule", "upfront_cost", "other"] as const;

async function AgreementCard({ a, org, orgId, shared }: { a: Assignment; org: string; orgId: string; shared: boolean }) {
  const t = await getTranslations("org.work");
  const tp = await getTranslations("org.programmes");
  const g = a.agreement;
  const locale = await getLocale();
  const number = (value: number) => new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
  const targetDate = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${g.target_date}T00:00:00Z`));
  const open = a.status === "assigned" || a.status === "change_requested";
  const courses = a.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, skill: s.skill_label || s.skill_id })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);
  return (
    <article className="a-card a-agreement" data-status={a.status}>
      <header className="a-agreement-head">
        <div>
          <div className="a-work-origin">
            <Building2 size={19} strokeWidth={1.6} aria-hidden />
            <div><strong>{org}</strong><small>{t("fundedLabel")}</small></div>
          </div>
          <h2>{g.title}</h2>
        </div>
        <span className="a-programme-status" data-status={a.status}>
          {t(`status.${a.status}`)}
        </span>
      </header>
      <section className="a-readiness" data-route={g.route} aria-label={t("termRoute")}>
        <div className="a-readiness-heading"><span>{t("termRoute")}</span><strong>{tp(`route.${g.route}`)}</strong></div>
        <div className="a-readiness-body">
          <div className="a-readiness-gauge" role="meter" aria-label={t("readinessCaption")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(g.readiness * 100)}>
            <svg viewBox="0 0 96 96" aria-hidden>
              <circle cx="48" cy="48" r="40" className="a-gauge-track" />
              <circle cx="48" cy="48" r="40" className="a-gauge-value" pathLength="100" strokeDasharray={`${Math.round(g.readiness * 100)} 100`} transform="rotate(-90 48 48)" />
            </svg>
            <strong>{Math.round(g.readiness * 100)}<small>%</small></strong>
          </div>
          <div className="a-readiness-role"><h3>{g.role_label}</h3><p>{t("readinessCaption")}</p></div>
        </div>
      </section>
      <dl className="a-terms">
        <div>
          <dt><CalendarDays size={15} aria-hidden />{t("termDate")}</dt>
          <dd><time dateTime={g.target_date}>{targetDate}</time></dd>
        </div>
        <div>
          <dt><Clock3 size={15} aria-hidden />{t("termTime")}</dt>
          <dd>{t("hoursWeek", { hours: g.hours_per_week })}</dd>
        </div>
        <div className="a-term-budget">
          <dt><Wallet size={15} aria-hidden />{t("termBudget")}</dt>
          <dd><strong>{t("budgetCap", { budget: number(g.budget_myr) })}</strong><small>{t("plannedCost", { cost: number(g.cost_myr) })}</small></dd>
        </div>
      </dl>
      <div className="a-programme-context">
        <span>{g.mandatory ? t("required") : t("optional")}</span>
        {g.objectives.length ? <p>{g.objectives.map((o) => tp(`objective.${o}`)).join(" · ")}</p> : null}
      </div>
      <details className="a-disclosure">
        <summary>{t("courses", { count: unique.length, weeks: a.pathway.total_weeks })}</summary>
        <ol className="a-rows">
          {unique.map((c) => (
            <li key={c.id}>
              <a href={c.url} target="_blank" rel="noreferrer">
                {c.title} <ArrowUpRight size={12} aria-hidden />
              </a>
              <span className="a-muted a-small">
                {c.skill} · {c.provider} · {t("courseLine", { hours: c.hours, cost: Math.round(c.cost_myr) })}
              </span>
            </li>
          ))}
        </ol>
        {(a.pathway.unmet ?? []).length ? (
          <p className="a-small a-muted">{t("unmet", { skills: (a.pathway.unmet ?? []).map((u) => u.label).join(", ") })}</p>
        ) : null}
      </details>
      <MetaBar meta={a.pathway.meta} />
      {a.status === "change_requested" ? (
        <p className="a-small a-muted">
          {t("changeSent", { reason: a.change_reason ? t(`reason.${a.change_reason}`) : "" })}
        </p>
      ) : null}
      {open ? (
        <footer className="a-agreement-actions">
          <ActionForm action={decideProgrammeAction} fields={{ programme_id: g.programme_id, decision: "accept", org_id: orgId }} label={t("accept")}>
            {shared ? null : (
              // Not sharing skill levels: accepting rebuilds the route from them, so ask first.
              <label className="a-check">
                <input type="checkbox" name="consent" required />
                <span>{t("acceptConsent", { org })}</span>
              </label>
            )}
          </ActionForm>
          {!g.mandatory ? (
            <ActionForm
              action={decideProgrammeAction}
              fields={{ programme_id: g.programme_id, decision: "decline", org_id: orgId }}
              label={t("decline")}
              variant="outline"
            />
          ) : null}
          <details className="a-disclosure">
            <summary>{t("askChange")}</summary>
            <ActionForm
              action={decideProgrammeAction}
              fields={{ programme_id: g.programme_id, decision: "request_change", org_id: orgId }}
              label={t("sendChange")}
              variant="outline"
              className="a-form-stack"
            >
              <label className="a-field">
                <span>{t("reasonLabel")}</span>
                <select name="reason" defaultValue="schedule" className="a-input">
                  {REASONS.map((r) => (
                    <option key={r} value={r}>
                      {t(`reason.${r}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="a-field">
                <span>{t("noteLabel")}</span>
                <textarea name="note" maxLength={500} rows={3} className="a-input" />
              </label>
            </ActionForm>
          </details>
        </footer>
      ) : null}
    </article>
  );
}

/** A member's programme agreements in this organisation, newest first. */
export async function WorkPlanView({ org }: { org: WorkspaceOption }) {
  const t = await getTranslations("org.work");
  const result = await fetchMyProgrammes();
  if (!result.ok) return <ErrorState failure={result} />;
  const { pending, accepted, closed } = byStatus(result.data.assignments);
  const all = [...pending, ...accepted, ...closed];
  return (
    <div className="a-view">
      <PageHeader eyebrow={org.name} title={t("planTitle")} description={t("planDesc", { org: org.name })} />
      <AssignedPackageView acceptedIds={accepted.map((a) => a.agreement.programme_id)} orgId={org.id} />
      {all.length ? (
        all.map((a) => <AgreementCard key={a.agreement.programme_id} a={a} org={org.name} orgId={org.id} shared={org.skills_shared} />)
      ) : (
        <EmptyState
          title={t("noProgrammes", { org: org.name })}
          description={t("noProgrammesHint")}
          action={
            <Link className="a-btn is-ghost" href="/app/pathway">
              {t("toPersonal")}
            </Link>
          }
        />
      )}
    </div>
  );
}
