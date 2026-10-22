import { ArrowUpRight, Award, BookOpen, Check } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader } from "@/components";
import { Ring } from "@/components/viz";
import type { ScenarioId } from "@/lib/api";
import { percent } from "@/lib/utils";

import { submitEvidenceAction, updateProgressAction } from "../actions";
import { fetchProgress } from "../api";
import { ActionForm } from "./ActionForm";
import { EvidenceBadge } from "./EvidenceBadge";
import { EvidenceForm } from "./EvidenceForm";

export async function ProgressView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const progress = await fetchProgress(roleId, scenario);
  if (!progress.ok) return <ApiError message={progress.message} />;
  const p = progress.data;
  // Courses come from the plan the API tracks progress against, so every button is valid.
  const courses = p.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, step: s.order })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);
  const done = unique.filter((c) => p.course_status[c.id] === "completed").length;

  return (
    <div className="a-stack" style={{ gap: 24 }}>
      <PageHeader eyebrow={d("progress")} title={t("progressTitle")} description={d("progressBody")}>
        <MetaBar meta={p.meta} />
      </PageHeader>

      <section className="a-metrics">
        <div className="a-card a-metric is-ring">
          <Ring value={p.percent_complete} size={120} stroke={11} caption={d("progress")} colour="var(--a-up)" />
          <span className="a-small a-muted">{t("progress.percent", { percent: percent(p.percent_complete) })}</span>
        </div>
        <div className="a-card a-metric">
          <span className="a-eyebrow">{t("progress.courses")}</span>
          <strong>
            {done}
            <small>/ {unique.length}</small>
          </strong>
          <div className="a-meter" aria-hidden>
            <i style={{ width: `${unique.length ? (done / unique.length) * 100 : 0}%` }} />
          </div>
        </div>
        <div className="a-card a-metric">
          <span className="a-eyebrow">{t("progress.skills")}</span>
          <strong>
            {p.gap_closed}
            <small>/ {p.gap_total}</small>
          </strong>
          <span className="a-small a-muted">{t("progress.gapClosed", { closed: p.gap_closed, total: p.gap_total })}</span>
        </div>
      </section>

      <section className="a-grid" style={{ alignItems: "start" }}>
        <div className="a-card a-span-7">
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
        </div>
        <div className="a-span-5 a-stack">
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
                    <strong>{b.label}</strong>
                    <small>
                      {t(`evidence.kind.${b.evidence ?? "self_reported"}`)} · {b.earned_at}
                    </small>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
