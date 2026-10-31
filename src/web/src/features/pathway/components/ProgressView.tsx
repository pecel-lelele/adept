import { ArrowUpRight, Award, BookOpen, Building2, Check, Layers, Target } from "lucide-react";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { ErrorState, Kpis, MetaBar, PageHeader } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { shareCompletionAction, submitEvidenceAction, updateProgressAction } from "../actions";
import { fetchProgress } from "../api";
import { ActionForm } from "./ActionForm";
import { EvidenceBadge } from "./EvidenceBadge";
import { EvidenceForm } from "./EvidenceForm";
import { MarkDoneFlow } from "./MarkDoneFlow";
import { ProgressToast } from "./ProgressToast";

/**
 * Progress on one plan. Personal workspace: the saved plan, counting the person's own work
 * learning too. Organisation workspace (`orgName`): the accepted employer programme, where
 * personal learning counts only after the member shares it.
 */
export async function ProgressView({
  roleId,
  scenario,
  orgName,
}: {
  roleId: string;
  scenario: ScenarioId;
  orgName?: string;
}) {
  const t = await getTranslations("pathway");
  const tw = await getTranslations("org.work");
  const d = await getTranslations("common.design");
  const tp = await getTranslations("ui.page");
  const progress = await fetchProgress(roleId, scenario);
  if (!progress.ok) return <ErrorState failure={progress} />;
  const p = progress.data;
  // Same rule the API applies to updates: a role in the URL does not start tracking it.
  if (p.trackable === false) redirect(`/app/matches?scenario=${scenario}&choose_role=1`);
  const isWork = p.workspace !== "personal";
  const elsewhere = p.completed_elsewhere ?? {};
  const reviewed = Object.values(p.evidence ?? {}).filter((e) => e.kind === "org_confirmed").length;
  // Courses come from the plan the API tracks progress against, so every button is valid.
  const courses = p.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, step: s.order })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);
  const history = p.history ?? [];
  const past = history.filter((item) => item.role_id !== roleId || !unique.some((c) => c.id === item.course.id));
  // Badge names come from translations keyed by the stable badge id, not the API's English text.
  const skillLabel = new Map(p.skills.map((s) => [s.skill_id, s.label]));
  const badgeLabel = (b: (typeof p.badges)[number]) => {
    const [kind, key] = b.id.split(":");
    if (kind === "skill" && b.skill_id) return t("badge.skill", { skill: b.skill_label || skillLabel.get(b.skill_id) || b.skill_id });
    if (key === "first" || key === "halfway" || key === "complete") return t(`badge.${key}`);
    return b.label;
  };
  const completedHistory = history.filter((item) => item.role_id === roleId && item.evidence?.kind !== "org_rejected");
  const done = new Set(completedHistory.map((item) => item.course.id)).size;
  const tracked = new Set([...unique.map((c) => c.id), ...completedHistory.map((item) => item.course.id)]).size;

  return (
    <div className="a-view">
      <ProgressToast />
      <PageHeader
        eyebrow={isWork ? p.pathway.role_label || d("progress") : undefined}
        title={isWork ? tw("progressTitle") : t("progressTitle")}
        description={isWork ? tw("progressDesc", { org: orgName ?? "" }) : tp("progressDesc")}
      >
        {isWork ? (
          <span className="a-chip a-workchip">
            <Building2 size={13} aria-hidden /> {tw("assignedByTeam", { org: orgName ?? "" })}
          </span>
        ) : null}
        <MetaBar meta={p.meta} />
      </PageHeader>

      <Kpis
        items={[
          {
            label: tp("kComplete"),
            value: `${Math.round(p.percent_complete * 100)}%`,
            icon: <Target size={15} />,
            tone: p.percent_complete >= 1 ? "up" : undefined,
            note: (
              <span className="a-kpi-bar" role="progressbar" aria-label={tp("kComplete")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(p.percent_complete * 100)}>
                <i style={{ width: `${Math.round(p.percent_complete * 100)}%` }} />
              </span>
            ),
          },
          {
            label: tp("kCoursesDone2"),
            value: done,
            unit: `/ ${tracked}`,
            icon: <BookOpen size={15} />,
            note: tp("kHoursWeighted"),
          },
          {
            label: t("progress.estimatedFit"),
            value: `${Math.round((p.estimated_skill_fit ?? 0) * 100)}%`,
            icon: <Target size={15} />,
            note: t("progress.fitNote"),
          },
          {
            label: tp("kGapClosed"),
            value: p.gap_closed,
            unit: `/ ${p.gap_total}`,
            icon: <Layers size={15} />,
            note: tp("gapClosedNote"),
          },
        ]}
      />

      <div className="a-split is-wide">
        <section className="a-card">
          <div className="a-card-head">
            <h2>{t("progress.courses")}</h2>
          </div>
          <p className="a-small a-muted" style={{ marginTop: -8 }}>
            {t("evidence.hint")}
          </p>
          <ul className="a-checklist-rows">
            {unique.map((c) => {
              const complete = p.course_status[c.id] === "completed";
              const ev = p.evidence?.[c.id];
              const doneElsewhere = complete ? undefined : elsewhere[c.id];
              if (doneElsewhere) {
                return (
                  <li key={c.id} data-done={!isWork}>
                    <span className="a-tickmark" aria-hidden>
                      <Check size={14} />
                    </span>
                    <div className="a-checklist-main">
                      <a href={c.url} target="_blank" rel="noreferrer">
                        {c.title} <ArrowUpRight size={13} aria-hidden />
                      </a>
                      <small>
                        {c.provider} · {isWork ? tw("donePersonally") : tw("doneAtWork")}
                      </small>
                    </div>
                    {isWork ? (
                      <ActionForm
                        action={shareCompletionAction}
                        className="a-inline-form"
                        fields={{ workspace: p.workspace, role_id: roleId, scenario, course_id: c.id }}
                        label={tw("share", { org: orgName ?? "" })}
                        variant="outline"
                      />
                    ) : null}
                  </li>
                );
              }
              return (
                <li key={c.id} data-done={complete}>
                  <span className="a-tickmark" aria-hidden>
                    {complete ? <Check size={14} /> : <BookOpen size={14} />}
                  </span>
                  <div className="a-checklist-main">
                    <a href={c.url} target="_blank" rel="noreferrer">
                      {c.title} <ArrowUpRight size={13} aria-hidden />
                    </a>
                    <small>
                      {c.provider} · {t("hours", { hours: c.hours })}
                    </small>
                    {complete ? (
                      <details className="a-disclosure">
                        <summary>{d("proof")}</summary>
                        <div>
                          <EvidenceBadge evidence={ev ?? null} />
                          {ev?.review_note ? <p className="a-small a-muted">{t("evidence.reviewNote", { note: ev.review_note })}</p> : null}
                          {ev?.kind !== "org_confirmed" ? (
                            <EvidenceForm action={submitEvidenceAction} fields={{ workspace: p.workspace, role_id: roleId, scenario, course_id: c.id }} />
                          ) : null}
                        </div>
                      </details>
                    ) : null}
                  </div>
                  {complete ? (
                    <ActionForm
                      action={updateProgressAction}
                      className="a-inline-form"
                      fields={{ workspace: p.workspace, role_id: roleId, scenario, course_id: c.id, status: "not_started" }}
                      label={t("progress.markUndone")}
                      variant="outline"
                    />
                  ) : (
                    <MarkDoneFlow
                      action={submitEvidenceAction}
                      fields={{ workspace: p.workspace, role_id: roleId, scenario, course_id: c.id }}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        </section>
        <aside className="a-aside">
          <div className="a-card">
            <div className="a-card-head">
              <h2>{t("progress.skills")}</h2>
            </div>
            <div className="a-levels-list">
              {p.skills.map((s) => (
                <div key={s.skill_id} className="a-level-row">
                  <span>{s.label}</span>
                  <div className="a-meter" aria-hidden>
                    <i style={{ width: `${Math.min(100, (s.current_level / Math.max(1, s.target_level)) * 100)}%` }} />
                  </div>
                  <small>{t("progress.level", { current: s.current_level, target: s.target_level })}</small>
                </div>
              ))}
            </div>
          </div>
          {isWork ? (
            <div className="a-card is-sage">
              <p className="a-small">{tw("kReviewed")}: {reviewed}</p>
              <p className="a-small" style={{ margin: 0 }}>
                {tw("privacyNote", { org: orgName ?? "" })}
              </p>
            </div>
          ) : (
          <div className="a-card is-sage">
            <div className="a-card-head">
              <h2>
                <Award size={16} aria-hidden /> {t("progress.badges")}
              </h2>
            </div>
            {p.badges.length === 0 ? (
              <p className="a-small a-muted" style={{ margin: 0 }}>
                {t("progress.noBadges")}
              </p>
            ) : (
              <div className="a-badges">
                {p.badges.map((b) => (
                  <span key={b.id} className="a-badge" data-kind={b.kind}>
                    <Award size={18} aria-hidden />
                    <strong>{badgeLabel(b)}</strong>
                    <small>
                      {t(`evidence.kind.${b.evidence ?? "self_reported"}`)} · {b.earned_at}
                    </small>
                  </span>
                ))}
              </div>
            )}
          </div>
          )}
        </aside>
      </div>

      {past.length > 0 ? (
        <section className="a-card">
          <div className="a-card-head"><h2>{t("history.title")}</h2></div>
          <p className="a-small a-muted">{t("history.description")}</p>
          <ul className="a-checklist-rows">
            {past.map((item) => {
              const c = item.course;
              const ev = item.evidence;
              return (
                <li key={`${item.role_id}:${c.id}`} data-done={ev?.kind !== "org_rejected"}>
                  <span className="a-tickmark" aria-hidden><Check size={14} /></span>
                  <div className="a-checklist-main">
                    <a href={c.url} target="_blank" rel="noreferrer">{c.title} <ArrowUpRight size={13} aria-hidden /></a>
                    <small>{c.provider} · {t("hours", { hours: c.hours })} · {item.role_label}</small>
                    <details className="a-disclosure">
                      <summary>{d("proof")}</summary>
                      <div>
                        <EvidenceBadge evidence={ev ?? null} />
                        {ev?.review_note ? <p className="a-small a-muted">{t("evidence.reviewNote", { note: ev.review_note })}</p> : null}
                        {ev?.kind !== "org_confirmed" ? (
                          <EvidenceForm action={submitEvidenceAction} fields={{ workspace: p.workspace, role_id: item.role_id, scenario, course_id: c.id }} />
                        ) : null}
                      </div>
                    </details>
                  </div>
                  <ActionForm
                    action={updateProgressAction}
                    className="a-inline-form"
                    fields={{ workspace: p.workspace, role_id: item.role_id, scenario, course_id: c.id, status: "not_started" }}
                    label={t("progress.markUndone")}
                    variant="outline"
                  />
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
