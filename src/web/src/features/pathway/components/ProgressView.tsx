import { ArrowUpRight, Award, BookOpen, Check, Layers, Target } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ApiError, Kpis, MetaBar, PageHeader } from "@/components";
import type { ScenarioId } from "@/lib/api";

import { submitEvidenceAction, updateProgressAction } from "../actions";
import { fetchProgress } from "../api";
import { ActionForm } from "./ActionForm";
import { EvidenceBadge } from "./EvidenceBadge";
import { EvidenceForm } from "./EvidenceForm";

export async function ProgressView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const tp = await getTranslations("ui.page");
  const progress = await fetchProgress(roleId, scenario);
  if (!progress.ok) return <ApiError message={progress.message} />;
  const p = progress.data;
  // Courses come from the plan the API tracks progress against, so every button is valid.
  const courses = p.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, step: s.order })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);
  // Badge names come from translations keyed by the stable badge id, not the API's English text.
  const skillLabel = new Map(p.skills.map((s) => [s.skill_id, s.label]));
  const badgeLabel = (b: (typeof p.badges)[number]) => {
    const [kind, key] = b.id.split(":");
    if (kind === "skill" && b.skill_id) return t("badge.skill", { skill: skillLabel.get(b.skill_id) ?? b.skill_id });
    if (key === "first" || key === "halfway" || key === "complete") return t(`badge.${key}`);
    return b.label;
  };
  const done = unique.filter((c) => p.course_status[c.id] === "completed").length;

  return (
    <div className="a-view">
      <PageHeader eyebrow={p.pathway.role_label || d("progress")} title={t("progressTitle")} description={tp("progressDesc")}>
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
              <span className="a-kpi-bar" aria-hidden>
                <i style={{ width: `${Math.round(p.percent_complete * 100)}%` }} />
              </span>
            ),
          },
          {
            label: tp("kCoursesDone2"),
            value: done,
            unit: `/ ${unique.length}`,
            icon: <BookOpen size={15} />,
            note: tp("kHoursWeighted"),
          },
          {
            label: tp("kGapClosed"),
            value: p.gap_closed,
            unit: `/ ${p.gap_total}`,
            icon: <Layers size={15} />,
            note: t("progress.gapClosed", { closed: p.gap_closed, total: p.gap_total }),
          },
          { label: tp("kBadges"), value: p.badges.length, icon: <Award size={15} />, note: tp("badgeNote") },
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
                        <summary>{d("details")}</summary>
                        <div>
                          <EvidenceBadge evidence={ev ?? null} />
                          {ev?.review_note ? <p className="a-small a-muted">{t("evidence.reviewNote", { note: ev.review_note })}</p> : null}
                          {ev?.kind !== "org_confirmed" ? (
                            <EvidenceForm action={submitEvidenceAction} fields={{ role_id: roleId, scenario, course_id: c.id }} />
                          ) : null}
                        </div>
                      </details>
                    ) : null}
                  </div>
                  <ActionForm
                    action={updateProgressAction}
                    className="a-inline-form"
                    fields={{ role_id: roleId, scenario, course_id: c.id, status: complete ? "not_started" : "completed" }}
                    label={complete ? t("progress.markUndone") : t("progress.markDone")}
                    variant={complete ? "outline" : "default"}
                  />
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
        </aside>
      </div>
    </div>
  );
}
