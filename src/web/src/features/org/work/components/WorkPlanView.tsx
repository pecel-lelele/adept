import { ArrowUpRight, Building2 } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, EmptyState, MetaBar, PageHeader } from "@/components";
import { AssignedPackageView } from "@/features/org/components/AssignedPackageView";
import { ActionForm } from "@/features/pathway/components/ActionForm";
import type { WorkspaceOption } from "@/lib/auth/workspaces";

import { decideProgrammeAction } from "../actions";
import { type Assignment, byStatus, fetchMyProgrammes } from "../api";

const REASONS = ["already_have_skill", "pace", "language", "accessibility", "schedule", "upfront_cost", "other"] as const;

async function AgreementCard({ a, org }: { a: Assignment; org: string }) {
  const t = await getTranslations("org.work");
  const tp = await getTranslations("org.programmes");
  const g = a.agreement;
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
        <div className="a-readiness-value"><strong>{Math.round(g.readiness * 100)}<small>%</small></strong><p>{t("readinessCaption")}</p></div>
        <div className="a-readiness-track" role="meter" aria-label={t("readinessCaption")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(g.readiness * 100)}>
          <span style={{ width: `${Math.round(g.readiness * 100)}%` }} />
        </div>
        <div className="a-readiness-scale" aria-hidden><span>0%</span><span>100%</span></div>
      </section>
      <dl className="a-terms">
        <div>
          <dt>{t("termRole")}</dt>
          <dd>{g.role_label}</dd>
        </div>
        <div>
          <dt>{t("termDate")}</dt>
          <dd>{g.target_date}</dd>
        </div>
        <div>
          <dt>{t("termTime")}</dt>
          <dd>{t("hoursWeek", { hours: g.hours_per_week })}</dd>
        </div>
        <div>
          <dt>{t("termBudget")}</dt>
          <dd>{t("budgetLine", { budget: Math.round(g.budget_myr), cost: Math.round(g.cost_myr) })}</dd>
        </div>
        <div>
          <dt>{t("termRequired")}</dt>
          <dd>{g.mandatory ? t("required") : t("optional")}</dd>
        </div>
        {g.objectives.length ? (
          <div>
            <dt>{t("termWhy")}</dt>
            <dd>{g.objectives.map((o) => tp(`objective.${o}`)).join(" · ")}</dd>
          </div>
        ) : null}
      </dl>
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
          <ActionForm action={decideProgrammeAction} fields={{ programme_id: g.programme_id, decision: "accept" }} label={t("accept")} />
          {!g.mandatory ? (
            <ActionForm
              action={decideProgrammeAction}
              fields={{ programme_id: g.programme_id, decision: "decline" }}
              label={t("decline")}
              variant="outline"
            />
          ) : null}
          <details className="a-disclosure">
            <summary>{t("askChange")}</summary>
            <ActionForm
              action={decideProgrammeAction}
              fields={{ programme_id: g.programme_id, decision: "request_change" }}
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
  if (!result.ok) return <ApiError message={result.message} />;
  const { pending, accepted, closed } = byStatus(result.data.assignments);
  const all = [...pending, ...accepted, ...closed];
  return (
    <div className="a-view">
      <PageHeader eyebrow={org.name} title={t("planTitle")} description={t("planDesc", { org: org.name })} />
      <AssignedPackageView acceptedIds={accepted.map((a) => a.agreement.programme_id)} />
      {all.length ? (
        all.map((a) => <AgreementCard key={a.agreement.programme_id} a={a} org={org.name} />)
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
