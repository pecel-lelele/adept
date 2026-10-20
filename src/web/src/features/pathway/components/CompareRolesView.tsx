import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  ApiError,
  Badge,
  buttonVariants,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetaBar,
  PageHeader,
  SdgBadge,
} from "@/components";
import type { ScenarioId, Schemas } from "@/lib/api";

import { savePlanAction } from "../actions";
import { fetchCompare } from "../api";
import { ActionForm } from "./ActionForm";

const DIRECTION_VARIANT = {
  rising: "success",
  stable: "secondary",
  declining: "danger",
  unknown: "outline",
} as const;

async function OptionCard({
  option,
  scenario,
}: {
  option: Schemas["RoleOption"];
  scenario: ScenarioId;
}) {
  const t = await getTranslations("pathway");
  const direction = option.trend_direction ?? "unknown";
  const query = `?role=${encodeURIComponent(option.role_id)}&scenario=${scenario}`;
  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle>{option.role_label}</CardTitle>
        <div className="flex flex-wrap gap-1">
          {option.is_saved_choice ? <Badge variant="success">{t("compare.yourChoice")}</Badge> : null}
          <Badge variant={DIRECTION_VARIANT[direction]}>
            {t(`compare.direction.${direction}`)}
            {option.trend_signal != null ? ` (${option.trend_signal.toFixed(2)})` : ""}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>
          {t("totalWeeks", { weeks: option.total_weeks })} ·{" "}
          {t("summary.totalHours", { hours: option.total_hours })} ·{" "}
          {t("compare.outOfPocket", { amount: option.out_of_pocket_myr })}
          {option.within_budget ? null : (
            <Badge variant="danger" className="ml-2">
              {t("summary.overBudget")}
            </Badge>
          )}
        </p>
        <p>
          {t("compare.skillsToClose", { count: option.skills_to_close })}
          {option.unmet_skills > 0 ? ` · ${t("compare.unmet", { count: option.unmet_skills })}` : ""}
        </p>
        <p className="text-xs text-muted-foreground">
          {t("compare.coverage", { percent: Math.round(option.trend_coverage * 100) })}
        </p>
        {(option.sdg_targets ?? []).length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {(option.sdg_targets ?? []).map((s) => (
              <SdgBadge key={s.target} target={s} />
            ))}
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Link
            href={`/app/pathway${query}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {t("compare.preview")}
          </Link>
          {option.is_saved_choice ? null : (
            <ActionForm
              action={savePlanAction}
              fields={{ role_id: option.role_id, scenario }}
              label={t("compare.choose")}
              className="flex flex-wrap items-center gap-2"
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/** Step between matches and the pathway: what each role would take, side by side, before the
 *  learner chooses. It does not rank roles (matching does) and never chooses for the learner. */
export async function CompareRolesView({
  scenario,
  roleIds = [],
}: {
  scenario: ScenarioId;
  roleIds?: string[];
}) {
  const t = await getTranslations("pathway");
  const result = await fetchCompare(scenario, roleIds);
  return (
    <section className="space-y-4">
      <PageHeader title={t("compare.title")} description={t("compare.description")}>
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            {t("compare.snapshot", { version: result.data.snapshot_version || "-" })}{" "}
            <Link href={`/app/matches?scenario=${scenario}`} className="underline">
              {t("compare.seeMatches")}
            </Link>
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {result.data.options.map((o) => (
              <OptionCard key={o.role_id} option={o} scenario={scenario} />
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            {t("compare.humanInCharge")} {t("estimateNote")}
          </p>
        </>
      )}
    </section>
  );
}
