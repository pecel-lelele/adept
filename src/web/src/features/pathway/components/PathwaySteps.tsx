import { getTranslations } from "next-intl/server";

import { Badge, Card, CardContent, CardHeader, CardTitle, SdgBadge } from "@/components";
import type { Schemas } from "@/lib/api";

type Course = Schemas["Course"];

async function CourseLine({ course }: { course: Course }) {
  const t = await getTranslations("pathway");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <a href={course.url} className="underline" target="_blank" rel="noreferrer">
        {course.title}
      </a>
      <span className="text-xs text-muted-foreground">
        {course.provider} · {t("hours", { hours: course.hours })}
      </span>
      <Badge variant="outline">
        {course.cost_myr === 0 ? t("free") : t("cost", { amount: course.cost_myr })}
      </Badge>
      {course.hrd_claimable ? (
        <Badge variant="success" title={course.hrd_note}>
          {t("hrdClaimable")}
        </Badge>
      ) : null}
      <span className="text-xs text-muted-foreground" title={course.duration_note}>
        {course.source ? `${t("step.source", { name: course.source.name })} · ` : null}
        {t("verified", { date: course.verified_at })}
      </span>
    </div>
  );
}

/** Ordered pathway steps. Also used by the organisation group plan (shows member counts). */
export async function PathwaySteps({
  steps,
  memberNames,
}: {
  steps: Schemas["PathwayStep"][];
  memberNames?: Record<string, string>;
}) {
  const t = await getTranslations("pathway");
  const label = (id: string) => steps.find((s) => s.skill_id === id)?.skill_label || id;
  return (
    <ol className="space-y-3">
      {steps.map((step) => (
        <li key={step.order}>
          <Card>
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-2">
              <CardTitle>
                {step.order}. {step.skill_label || step.skill_id}
              </CardTitle>
              <span className="text-xs text-muted-foreground">
                {t("weeks", { start: step.week_start, end: step.week_end })} ·{" "}
                {t("hours", { hours: step.est_hours })}
              </span>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="font-medium">
                {t("step.levels", {
                  current: step.current_level ?? 0,
                  reaches: step.reaches_level ?? 0,
                  target: step.target_level ?? 1,
                })}
              </p>
              <p className="text-xs text-muted-foreground">{step.reason}</p>
              {step.prerequisites && step.prerequisites.length > 0 ? (
                <p className="text-xs">
                  {t("step.prerequisites", { skills: step.prerequisites.map(label).join(", ") })}
                </p>
              ) : null}
              {step.courses.map((c) => (
                <CourseLine key={c.id} course={c} />
              ))}
              {step.sdg_targets && step.sdg_targets.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-xs text-muted-foreground">{t("step.sdg")}:</span>
                  {step.sdg_targets.map((s) => (
                    <SdgBadge key={s.target} target={s} />
                  ))}
                </div>
              ) : null}
              {memberNames && step.member_ids && step.member_ids.length > 0 ? (
                <p className="text-xs">
                  {t("step.members", {
                    count: step.member_ids.length,
                    members: step.member_ids.map((id) => memberNames[id] ?? id).join(", "),
                  })}
                </p>
              ) : null}
              {step.alternatives && step.alternatives.length > 0 ? (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground">
                    {t("step.alternatives", { count: step.alternatives.length })}
                  </summary>
                  <div className="mt-2 space-y-1">
                    {step.alternatives.map((c) => (
                      <CourseLine key={c.id} course={c} />
                    ))}
                  </div>
                </details>
              ) : null}
            </CardContent>
          </Card>
        </li>
      ))}
    </ol>
  );
}
