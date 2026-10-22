import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
} from "@/components";
import type { ScenarioId } from "@/lib/api";
import { cn, percent } from "@/lib/utils";

import { submitEvidenceAction, updateProgressAction } from "../actions";
import { fetchProgress } from "../api";
import { ActionForm } from "./ActionForm";
import { EvidenceBadge } from "./EvidenceBadge";
import { EvidenceForm } from "./EvidenceForm";

export async function ProgressView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway"), d = await getTranslations("common.design");
  const progress = await fetchProgress(roleId, scenario);
  if (!progress.ok) return <ApiError message={progress.message} />;
  const p = progress.data;
  // Courses come from the plan the API tracks progress against, so every button is valid.
  const courses = p.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, step: s.order })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);

  return (
    <section className="space-y-4 progress-page">
      <PageHeader title={t("progressTitle")} description={d("progressBody")}>
        <MetaBar meta={p.meta} />
      </PageHeader>
      <Card>
        <CardContent className="space-y-2 pt-4 text-sm">
          <p>{t("progress.percent", { percent: percent(p.percent_complete) })}</p>
          <div className="h-2 rounded bg-muted">
            <div className="h-2 rounded bg-primary" style={{ width: percent(p.percent_complete) }} />
          </div>
          <p className="text-muted-foreground">
            {t("progress.gapClosed", { closed: p.gap_closed, total: p.gap_total })}
          </p>
          <p className="text-xs text-muted-foreground">{t("evidence.hint")}</p>
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("progress.courses")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {unique.map((c) => {
              const done = p.course_status[c.id] === "completed";
              const ev = p.evidence?.[c.id];
              return (
                <div key={c.id} className="progress-course space-y-1">
                  <a href={c.url} target="_blank" rel="noreferrer" className="progress-course-link">{c.title} ↗</a>
                  <ActionForm
                    action={updateProgressAction}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1"
                    fields={{
                      role_id: roleId,
                      scenario,
                      course_id: c.id,
                      status: done ? "not_started" : "completed",
                    }}
                    label={done ? t("progress.markUndone") : t("progress.markDone")}
                    variant={done ? "outline" : "default"}
                  >
                    <span
                      className={cn(
                        "min-w-0 flex-1",
                        done ? "text-muted-foreground line-through" : undefined,
                      )}
                    >
                      {c.provider} · {c.hours} h
                    </span>
                  </ActionForm>
                  {done ? (
                    <details className="step-explanation"><summary>{d("details")}</summary><div className="space-y-1">
                      <EvidenceBadge evidence={ev ?? null} />
                      {ev?.review_note ? (
                        <p className="text-xs text-muted-foreground">
                          {t("evidence.reviewNote", { note: ev.review_note })}
                        </p>
                      ) : null}
                      {ev?.kind !== "org_confirmed" ? (
                        <EvidenceForm
                          action={submitEvidenceAction}
                          fields={{ role_id: roleId, scenario, course_id: c.id }}
                        />
                      ) : null}
                    </div></details>
                  ) : null}
                </div>
              );
            })}
          </CardContent>
        </Card>
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("progress.skills")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {p.skills.map((s) => (
                <div key={s.skill_id} className="flex justify-between">
                  <span>{s.label}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {t("progress.level", { current: s.current_level, target: s.target_level })}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>{t("progress.badges")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2 text-sm">
              {p.badges.length === 0 ? (
                <p className="text-muted-foreground">{t("progress.noBadges")}</p>
              ) : (
                p.badges.map((b) => (
                  <Badge key={b.id} variant={b.kind === "skill" ? "success" : "secondary"}>
                    {b.label} · {t(`evidence.kind.${b.evidence ?? "self_reported"}`)} · {b.earned_at}
                  </Badge>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
