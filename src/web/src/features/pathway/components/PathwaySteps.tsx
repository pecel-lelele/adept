import { ArrowUpRight, BookOpen, Clock3 } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { SdgBadge } from "@/components";
import type { Schemas } from "@/lib/api";

/** One course in a step: icon tile, title (opens the provider), provider and hours, cost. */
export async function CourseLine({ course }: { course: Schemas["Course"] }) {
  const t = await getTranslations("pathway");
  const free = course.cost_myr === 0;
  return (
    <a className="a-course-row" href={course.url} target="_blank" rel="noreferrer">
      <span className="a-course-icon" aria-hidden>
        <BookOpen size={18} strokeWidth={1.6} />
      </span>
      <span className="a-course-main">
        <strong>
          {course.title} <ArrowUpRight size={13} aria-hidden />
        </strong>
        <small>
          {course.provider} · {t("hours", { hours: course.hours })}
          {course.hrd_claimable ? ` · ${t("hrdClaimable")}` : ""}
        </small>
      </span>
      <span className="a-chip" data-tone={free ? "up" : undefined}>
        {free ? t("free") : t("cost", { amount: course.cost_myr })}
      </span>
    </a>
  );
}

/** The ordered plan: numbered step cards on a rail, each with its courses and reasons. */
export async function PathwaySteps({
  steps,
  memberNames,
  courseStatus = {},
}: {
  steps: Schemas["PathwayStep"][];
  memberNames?: Record<string, string>;
  courseStatus?: Record<string, string>;
}) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const label = (id: string) => steps.find((s) => s.skill_id === id)?.skill_label || id;
  return (
    <ol className="a-steps">
      {steps.map((step, i) => {
        const stepDone =
          step.courses.length > 0 &&
          step.courses.every((c) => courseStatus[c.id] === "completed");
        const allPrevDone = steps
          .slice(0, i)
          .every(
            (prev) =>
              prev.courses.length > 0 &&
              prev.courses.every((c) => courseStatus[c.id] === "completed"),
          );
        const stepState: "done" | "current" | "todo" = stepDone
          ? "done"
          : allPrevDone
            ? "current"
            : "todo";
        return (
        <li key={step.order} className="a-step-item" data-state={stepState}>
          <span className="a-step-num" aria-hidden>
            {stepDone ? "✓" : String(step.order).padStart(2, "0")}
          </span>
          <article className="a-card a-step-card">
            <header className="a-step-head">
              <div>
                <span className="a-eyebrow">
                  {t("weeks", { start: step.week_start, end: step.week_end })}
                </span>
                <h2>{step.skill_label || step.skill_id}</h2>
              </div>
              <span className="a-chip">
                <Clock3 size={12} aria-hidden /> {t("hours", { hours: step.est_hours })}
              </span>
            </header>
            <div className="a-course-list">
              {step.courses.map((c) => (
                <CourseLine key={c.id} course={c} />
              ))}
            </div>
            {step.sdg_targets?.length ? (
              <div className="a-chips">
                {step.sdg_targets.map((s) => (
                  <SdgBadge key={s.target} target={s} />
                ))}
              </div>
            ) : null}
            <details className="a-disclosure">
              <summary>{d("stepDetails")}</summary>
              <div>
                <p>{step.reason}</p>
                <p>
                  {t("step.levels", {
                    current: step.current_level ?? 0,
                    reaches: step.reaches_level ?? 0,
                    target: step.target_level ?? 1,
                  })}
                </p>
                {step.prerequisites?.length ? (
                  <p>{t("step.prerequisites", { skills: step.prerequisites.map(label).join(", ") })}</p>
                ) : null}
                {step.courses.map((c) => (
                  <p key={c.id} className="a-small a-muted">
                    {c.source?.name} · {t("verified", { date: c.verified_at })}
                    {c.hrd_claimable ? ` · ${t("hrdClaimable")}` : ""}
                    {c.price_note ? ` · ${c.price_note}` : ""}
                    {c.hrd_note ? ` · ${c.hrd_note}` : ""}
                    {c.duration_note ? ` · ${c.duration_note}` : ""}
                  </p>
                ))}
                {memberNames && step.member_ids?.length ? (
                  <p>
                    {t("step.members", {
                      count: step.member_ids.length,
                      members: step.member_ids.map((id) => memberNames[id] ?? id).join(", "),
                    })}
                  </p>
                ) : null}
              </div>
            </details>
            {step.alternatives?.length ? (
              <details className="a-disclosure">
                <summary>{t("step.alternatives", { count: step.alternatives.length })}</summary>
                <div className="a-course-list">
                  {step.alternatives.map((c) => (
                    <CourseLine key={c.id} course={c} />
                  ))}
                </div>
              </details>
            ) : null}
          </article>
        </li>
        );
      })}
    </ol>
  );
}
