import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
} from "@/components";
import type { ScenarioId } from "@/lib/api";
import { percent } from "@/lib/utils";

import { updateProgressAction } from "../actions";
import { fetchProgress } from "../api";

export async function ProgressView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const progress = await fetchProgress(roleId, scenario);
  if (!progress.ok) return <ApiError message={progress.message} />;
  const p = progress.data;
  // Courses come from the plan the API tracks progress against, so every button is valid.
  const courses = p.pathway.steps.flatMap((s) => s.courses.map((c) => ({ ...c, step: s.order })));
  const unique = courses.filter((c, i) => courses.findIndex((x) => x.id === c.id) === i);

  return (
    <section className="space-y-4">
      <PageHeader title={t("progressTitle")} description={t("progressBody")}>
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
              return (
                <form key={c.id} action={updateProgressAction} className="flex items-center gap-2">
                  <input type="hidden" name="role_id" value={roleId} />
                  <input type="hidden" name="scenario" value={scenario} />
                  <input type="hidden" name="course_id" value={c.id} />
                  <input type="hidden" name="status" value={done ? "not_started" : "completed"} />
                  <Button size="sm" variant={done ? "outline" : "default"}>
                    {done ? t("progress.markUndone") : t("progress.markDone")}
                  </Button>
                  <span className={done ? "line-through text-muted-foreground" : undefined}>
                    {c.step}. {c.title}
                  </span>
                </form>
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
                    {b.label} · {t("progress.selfReported")} · {b.earned_at}
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
