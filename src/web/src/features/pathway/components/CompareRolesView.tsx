import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Badge, EmptyState, ErrorState, MetaBar, PageHeader, SdgBadge } from "@/components";
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
  snapshotDate,
}: {
  option: Schemas["RoleOption"];
  scenario: ScenarioId;
  snapshotDate?: string;
}) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const direction = option.trend_direction ?? "unknown";
  const query = `?role=${encodeURIComponent(option.role_id)}&scenario=${scenario}${snapshotDate ? "&snapshot_date=" + encodeURIComponent(snapshotDate) : ""}`;
  const coverage = Math.round(option.trend_coverage * 100);
  return (
    <article className="a-card a-option" data-chosen={option.is_saved_choice || undefined}>
      <header className="a-card-top">
        <h2 className="a-card-title" style={{ fontSize: 20 }}>
          {option.role_label}
        </h2>
        <div className="a-chips">
          {option.is_saved_choice ? <Badge variant="success">{t("compare.yourChoice")}</Badge> : null}
          <Badge variant={DIRECTION_VARIANT[direction]}>{t(`compare.direction.${direction}`)}</Badge>
        </div>
      </header>
      <div className="a-stats">
        <div className="a-stat">
          <strong>{option.total_weeks}</strong>
          <span>{d("duration")}</span>
        </div>
        <div className="a-stat">
          <strong>{option.total_hours}</strong>
          <span>h</span>
        </div>
        <div className="a-stat">
          <strong>
            <small>RM</small>
            {option.out_of_pocket_myr}
          </strong>
          <span>{d("cost")}</span>
        </div>
      </div>
      {option.within_budget ? null : <Badge variant="danger">{t("summary.overBudget")}</Badge>}
      <p className="a-small" style={{ margin: 0 }}>
        {t("compare.skillsToClose", { count: option.skills_to_close })}
        {option.unmet_skills > 0 ? ` · ${t("compare.unmet", { count: option.unmet_skills })}` : ""}
      </p>
      <div className="a-coverage">
        <div className="a-meter" aria-hidden>
          <i style={{ width: `${coverage}%` }} />
        </div>
        <small>{t("compare.coverage", { percent: coverage })}</small>
      </div>
      {(option.sdg_targets ?? []).length > 0 ? (
        <div className="a-chips">
          {(option.sdg_targets ?? []).map((s) => (
            <SdgBadge key={s.target} target={s} />
          ))}
        </div>
      ) : null}
      <div className="a-hero-actions" style={{ marginTop: "auto" }}>
        <Link href={`/app/pathway${query}`} className="a-btn is-ghost is-small">
          {t("compare.preview")} <ArrowUpRight size={14} aria-hidden />
        </Link>
        {option.is_saved_choice || snapshotDate ? null : (
          <ActionForm action={savePlanAction} fields={{ role_id: option.role_id, scenario }} label={t("compare.choose")} className="a-inline-form" />
        )}
      </div>
    </article>
  );
}

/** Step between matches and the pathway: what each role would take, side by side, before the
 *  learner chooses. It does not rank roles (matching does) and never chooses for the learner. */
export async function CompareRolesView({
  scenario,
  roleIds = [],
  snapshotDate,
}: {
  scenario: ScenarioId;
  roleIds?: string[];
  snapshotDate?: string;
}) {
  const t = await getTranslations("pathway");
  const result = await fetchCompare(scenario, roleIds, snapshotDate);
  return (
    <div className="a-stack" style={{ gap: 24 }}>
      <PageHeader
        title={t("compare.title")}
        description={t("compare.description")}
        actions={
          <Link
            href={`/app/matches?scenario=${scenario}${snapshotDate ? "&snapshot_date=" + encodeURIComponent(snapshotDate) : ""}`}
            className="a-btn is-ghost is-small"
          >
            {t("compare.seeMatches")}
          </Link>
        }
      >
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <>
          {result.data.options.length === 0 ? (
            <EmptyState title={t("compare.emptyTitle")} description={t("compare.emptyHint")} action={
              <Link href={`/app/matches?scenario=${scenario}`} className="a-btn is-small">{t("compare.seeMatches")}</Link>
            } />
          ) : null}
          <div className="a-grid a-options">
            {result.data.options.map((o) => (
              <div key={o.role_id} className="a-span-6">
                <OptionCard option={o} scenario={scenario} snapshotDate={snapshotDate} />
              </div>
            ))}
          </div>
          <p className="a-notice" data-tone="info">
            {t("compare.humanInCharge")} {t("estimateNote")}
          </p>
        </>
      )}
    </div>
  );
}
