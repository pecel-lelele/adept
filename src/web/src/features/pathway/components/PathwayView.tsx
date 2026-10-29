import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarRange,
  Check,
  Clock3,
  GitCompareArrows,
  Hourglass,
  Leaf,
  Target,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, Kpis, MetaBar, PageHeader } from "@/components";
import { Fold } from "@/components/Fold";
import { HistoricalSnapshotBanner } from "@/components/HistoricalSnapshotBanner";
import { CareerRoadmap, CertificationsCard, RoleOpeningsCard } from "@/features/jobs";
import type { ScenarioId, Schemas } from "@/lib/api";

import { acceptReplanAction, savePlanAction } from "../actions";
import { fetchPathway, fetchPlanStatus } from "../api";
import { ActionForm } from "./ActionForm";
import { PathwaySteps } from "./PathwaySteps";

/** The plan's four numbers: how long, how many hours a week, hours in total, what it costs. */
async function Summary({ plan }: { plan: Schemas["Pathway"] }) {
  const tp = await getTranslations("ui.page");
  const t = await getTranslations("pathway");
  const over = plan.within_budget === false;
  return (
    <Kpis
      items={[
        { label: tp("kDuration"), value: plan.total_weeks, unit: tp("weeksUnit"), icon: <CalendarRange size={15} />, note: tp("estimate") },
        { label: tp("kTime"), value: plan.hours_per_week ?? 0, unit: tp("hPerWeek"), icon: <Clock3 size={15} />, note: tp("fromProfile") },
        { label: tp("kTotalHours"), value: plan.total_hours ?? 0, unit: "h", icon: <Hourglass size={15} />, note: tp("kSteps", { count: plan.steps.length }) },
        {
          label: tp("kCost"),
          value: `RM ${(plan.out_of_pocket_myr ?? 0).toLocaleString("en-MY")}`,
          icon: <Wallet size={15} />,
          tone: over ? "warn" : undefined,
          note: over ? t("summary.overBudget") : tp("withinBudget", { budget: plan.budget_myr ?? 0 }),
        },
      ]}
    />
  );
}

/** Side column: where to go from the plan, then the plan's notes in full. */
async function PlanAside({ plan, query }: { plan: Schemas["Pathway"]; query: string }) {
  const t = await getTranslations("pathway");
  const tp = await getTranslations("ui.page");
  const links = [
    { to: `/app/progress${query}`, icon: <Target size={16} aria-hidden />, label: t("plan.progressLink") },
    { to: `/app/sdg${query}`, icon: <Leaf size={16} aria-hidden />, label: t("plan.sdgLink") },
    { to: `/app/courses${query}`, icon: <BookOpen size={16} aria-hidden />, label: t("catalogue.browse") },
    { to: `/app/pathway/compare${query}`, icon: <GitCompareArrows size={16} aria-hidden />, label: t("compare.link") },
  ];
  return (
    <aside className="a-aside is-sticky">
      <nav className="a-card a-flush" aria-label={tp("usePlan")}>
        <div className="a-card-head a-pad">
          <h2>{tp("usePlan")}</h2>
        </div>
        <ul className="a-linklist">
          {links.map((l) => (
            <li key={l.to}>
              <Link href={l.to}>
                {l.icon}
                <span>{l.label}</span>
                <ArrowRight size={14} aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <details className="a-card is-sage a-fold">
        <summary className="a-fold-head">
          <span className="a-fold-title">{tp("planNotes")}</span>
        </summary>
        <ul className="a-notes a-fold-body">
          <li>{t("summary.outOfPocket", { amount: plan.out_of_pocket_myr ?? 0, budget: plan.budget_myr ?? 0 })}</li>
          {plan.hrd_eligible ? <li>{t("summary.hrdNote")}</li> : null}
          {(plan.warnings ?? []).map((w) => (
            <li key={w}>{w}</li>
          ))}
          <li>{t("estimateNote")}</li>
        </ul>
      </details>
    </aside>
  );
}

async function ReplanBanner({ status }: { status: Schemas["ReplanStatus"] }) {
  const t = await getTranslations("pathway");
  if (!status.needs_replan) return null;
  // Show skill names, not ids: they appear in the saved plan or the proposed one.
  const names = new Map(
    [...(status.saved?.pathway.steps ?? []), ...(status.proposed?.steps ?? [])].map((s) => [s.skill_id, s.skill_label]),
  );
  const skillName = (id: string) => names.get(id) || id;
  return (
    <section className="a-notice a-replan" role="status">
      <div style={{ display: "grid", gap: 8, minWidth: 0 }}>
        <strong>{t("replan.title")}</strong>
        <span>{status.message}</span>
        <ul>
          {status.changes.map((c) => (
            <li key={`${c.kind}-${c.skill_id}`}>
              {t(`replan.change.${c.kind}`)}: {skillName(c.skill_id)}. {c.detail}
            </li>
          ))}
        </ul>
        <div className="a-hero-actions">
          <ActionForm action={acceptReplanAction} label={t("replan.accept")} />
          <span className="a-small">{t("replan.keep")}</span>
        </div>
      </div>
    </section>
  );
}

export async function PathwayView({
  roleId,
  scenario,
  snapshotDate,
}: {
  roleId: string;
  scenario: ScenarioId;
  snapshotDate?: string;
}) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const tp = await getTranslations("ui.page");
  const [result, status] = await Promise.all([fetchPathway(roleId, scenario, snapshotDate), fetchPlanStatus()]);
  const tm = await getTranslations("matching");
  if (!result.ok) return <ApiError message={result.message} />;
  const saved = status.ok ? status.data.saved : null;
  // The saved plan is the one progress is tracked against; show it (not a fresh rebuild)
  // whenever it is for this role and scenario. Changes are offered by the re-plan banner.
  const savedHere =
    !snapshotDate && saved && saved.role_id === roleId && saved.scenario === scenario ? saved : null;
  const plan = savedHere ? savedHere.pathway : result.data;
  const query = `?role=${encodeURIComponent(roleId)}&scenario=${scenario}`;

  const action = snapshotDate ? (
    <Link href={`/app/pathway${query}`} className="a-btn is-ghost is-small">
      {tm("viewLatestPathway")} <ArrowUpRight size={15} aria-hidden />
    </Link>
  ) : savedHere ? (
    <span className="a-chip" data-tone="up">
      <Check size={13} aria-hidden /> {t("plan.saved", { date: savedHere.saved_at.slice(0, 10) })}
    </span>
  ) : (
    <ActionForm action={savePlanAction} fields={{ role_id: roleId, scenario }} label={t("plan.save")} className="a-inline-form" />
  );

  return (
    <div className="a-view">
      <PageHeader
        eyebrow={tp("stepOf", { step: 4 })}
        title={plan.role_label || plan.role_id}
        description={`${t("totalWeeks", { weeks: plan.total_weeks })} · ${d("pathBody")}`}
        actions={action}
      >
        <MetaBar meta={plan.meta} />
      </PageHeader>
      <HistoricalSnapshotBanner date={snapshotDate} latestHref={`/app/pathway${query}`} />
      {!savedHere && !snapshotDate ? <p className="a-notice" data-tone="info">{t("plan.decide")}</p> : null}
      {status.ok && savedHere ? <ReplanBanner status={status.data} /> : null}
      <Summary plan={plan} />
      {!snapshotDate ? <CareerRoadmap plan={plan} scenario={scenario} /> : null}

      <div className="a-split is-wide">
        <div className="a-stack">
          <PathwaySteps steps={plan.steps} />
          {(plan.unmet ?? []).length > 0 ? (
            <Fold title={t("unmet.title")} meta={t("unmet.count", { count: (plan.unmet ?? []).length })}>
              <ul className="a-jobs">
                {(plan.unmet ?? []).map((u) => (
                  <li key={u.skill_id} className="a-job">
                    <div className="a-job-main">
                      <strong className="a-job-title">{u.label}</strong>
                      <span className="a-job-where">{t(`unmet.${u.reason}`)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </Fold>
          ) : null}
          {!snapshotDate ? (
            <>
              <CertificationsCard roleId={plan.role_id} scenario={scenario} />
              <RoleOpeningsCard roleId={plan.role_id} scenario={scenario} limit={4} />
            </>
          ) : null}
        </div>
        <PlanAside plan={plan} query={query} />
      </div>
    </div>
  );
}
