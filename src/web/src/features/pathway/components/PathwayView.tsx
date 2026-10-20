import Link from "next/link";
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
import type { ScenarioId, Schemas } from "@/lib/api";

import { acceptReplanAction, savePlanAction } from "../actions";
import { fetchPathway, fetchPlanStatus } from "../api";
import { ActionForm } from "./ActionForm";
import { PathwaySteps } from "./PathwaySteps";
import { SegmentGuide } from "./SegmentGuide";

async function Summary({ plan }: { plan: Schemas["Pathway"] }) {
  const t = await getTranslations("pathway");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("summary.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-sm">
        <p>
          {t("totalWeeks", { weeks: plan.total_weeks })} ·{" "}
          {t("summary.pace", { hours: plan.hours_per_week ?? 0 })} ·{" "}
          {t("summary.totalHours", { hours: plan.total_hours ?? 0 })}
        </p>
        <p>
          {t("summary.outOfPocket", {
            amount: plan.out_of_pocket_myr ?? 0,
            budget: plan.budget_myr ?? 0,
          })}
          {plan.within_budget === false ? (
            <Badge variant="danger" className="ml-2">
              {t("summary.overBudget")}
            </Badge>
          ) : null}
        </p>
        {(plan.total_cost_myr ?? 0) > 0 ? (
          <p className="text-muted-foreground">
            {t("summary.listPrice", { amount: plan.total_cost_myr ?? 0 })}
          </p>
        ) : null}
        {plan.hrd_eligible ? (
          <p className="text-xs text-muted-foreground">{t("summary.hrdNote")}</p>
        ) : null}
        {(plan.warnings ?? []).map((w) => (
          <p key={w} className="text-xs text-amber-800">
            {w}
          </p>
        ))}
        <p className="text-xs text-muted-foreground">
          {t("catalogueOnly")} {t("estimateNote")}
        </p>
      </CardContent>
    </Card>
  );
}

async function ReplanBanner({ status }: { status: Schemas["ReplanStatus"] }) {
  const t = await getTranslations("pathway");
  if (!status.needs_replan) return null;
  return (
    <Card className="border-amber-400 bg-amber-50">
      <CardHeader>
        <CardTitle>{t("replan.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{status.message}</p>
        <ul className="list-disc pl-5 text-xs">
          {status.changes.map((c) => (
            <li key={`${c.kind}-${c.skill_id}`}>
              {t(`replan.change.${c.kind}`)}: {c.skill_id}. {c.detail}
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <ActionForm action={acceptReplanAction} label={t("replan.accept")} />
          <span className="self-center text-xs text-muted-foreground">{t("replan.keep")}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export async function PathwayView({ roleId, scenario }: { roleId: string; scenario: ScenarioId }) {
  const t = await getTranslations("pathway");
  const [result, status] = await Promise.all([fetchPathway(roleId, scenario), fetchPlanStatus()]);
  if (!result.ok) return <ApiError message={result.message} />;
  const saved = status.ok ? status.data.saved : null;
  // The saved plan is the one progress is tracked against; show it (not a fresh rebuild)
  // whenever it is for this role and scenario. Changes are offered by the re-plan banner.
  const savedHere = saved && saved.role_id === roleId && saved.scenario === scenario ? saved : null;
  const plan = savedHere ? savedHere.pathway : result.data;
  const query = `?role=${encodeURIComponent(roleId)}&scenario=${scenario}`;

  return (
    <section className="space-y-4">
      <PageHeader
        title={`${t("title")}: ${plan.role_label || plan.role_id}`}
        description={t("totalWeeks", { weeks: plan.total_weeks })}
      >
        <MetaBar meta={plan.meta} />
      </PageHeader>
      {status.ok && savedHere ? <ReplanBanner status={status.data} /> : null}
      <Summary plan={plan} />
      <SegmentGuide segment={plan.segment} scenario={scenario} />
      <div className="flex flex-wrap items-center gap-2">
        {savedHere ? (
          <Badge variant="success">
            {t("plan.saved", { date: savedHere.saved_at.slice(0, 10) })}
          </Badge>
        ) : (
          <ActionForm
            action={savePlanAction}
            fields={{ role_id: roleId, scenario }}
            label={t("plan.save")}
          />
        )}
        <Link href={`/app/progress${query}`} className="text-sm underline">
          {t("plan.progressLink")}
        </Link>
        <Link href={`/app/sdg${query}`} className="text-sm underline">
          {t("plan.sdgLink")}
        </Link>
        <Link href="/app/courses" className="text-sm underline">
          {t("catalogue.browse")}
        </Link>
        <Link href={`/app/pathway/compare?scenario=${scenario}`} className="text-sm underline">
          {t("compare.link")}
        </Link>
      </div>
      <p className="text-xs text-muted-foreground">{t("plan.decide")}</p>
      <PathwaySteps steps={plan.steps} />
      {(plan.unmet ?? []).length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("unmet.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(plan.unmet ?? []).map((u) => (
              <div key={u.skill_id}>
                <span className="font-medium">{u.label}</span>{" "}
                <Badge variant="warning">{t(`unmet.${u.reason}`)}</Badge>
                <p className="text-xs text-muted-foreground">{u.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}
