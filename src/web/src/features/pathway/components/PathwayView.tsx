import { ArrowUpRight, BookOpen, Check, GitCompareArrows, Leaf, Target } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, MetaBar, PageHeader } from "@/components";
import { StepTrack } from "@/components/viz";
import type { ScenarioId, Schemas } from "@/lib/api";

import { acceptReplanAction, savePlanAction } from "../actions";
import { fetchPathway, fetchPlanStatus } from "../api";
import { ActionForm } from "./ActionForm";
import { PathwaySteps } from "./PathwaySteps";

/** Three headline numbers and the step track, then the plan's fine print on request. */
async function Summary({ plan }: { plan: Schemas["Pathway"] }) {
  const t = await getTranslations("pathway");
  const d = await getTranslations("common.design");
  const metrics = [
    { label: d("duration"), value: plan.total_weeks, unit: "" },
    { label: d("pace"), value: plan.hours_per_week ?? 0, unit: "h" },
    { label: d("cost"), value: plan.out_of_pocket_myr ?? 0, unit: "RM" },
  ];
  return (
    <section className="a-metrics">
      {metrics.map((m) => (
        <div key={m.label} className="a-card a-metric">
          <span className="a-eyebrow">{m.label}</span>
          <strong>
            {m.unit === "RM" ? <small>RM</small> : null}
            {m.value}
            {m.unit === "h" ? <small>h</small> : null}
          </strong>
        </div>
      ))}
      <div className="a-card a-metric is-track">
        <span className="a-eyebrow">{t("summary.title")}</span>
        <StepTrack
          steps={plan.steps.slice(0, 6).map((s, i) => ({
            id: s.skill_id,
            label: s.skill_label || s.skill_id,
            state: i === 0 ? "current" : "todo",
          }))}
        />
      </div>
      {plan.within_budget === false ? (
        <p className="a-notice is-full" role="status">
          {t("summary.overBudget")}
        </p>
      ) : null}
      <details className="a-disclosure is-full">
        <summary>{d("planDetails")}</summary>
        <div>
          <p>
            {t("summary.totalHours", { hours: plan.total_hours ?? 0 })} ·{" "}
            {t("summary.outOfPocket", { amount: plan.out_of_pocket_myr ?? 0, budget: plan.budget_myr ?? 0 })}
          </p>
          {plan.hrd_eligible ? <p>{t("summary.hrdNote")}</p> : null}
          {(plan.warnings ?? []).map((w) => (
            <p key={w}>{w}</p>
          ))}
          <p className="a-muted">{t("estimateNote")}</p>
        </div>
      </details>
    </section>
  );
}

async function ReplanBanner({ status }: { status: Schemas["ReplanStatus"] }) {
  const t = await getTranslations("pathway");
  if (!status.needs_replan) return null;
  return (
    <section className="a-notice a-replan" role="status">
      <div style={{ display: "grid", gap: 8, minWidth: 0 }}>
        <strong>{t("replan.title")}</strong>
        <span>{status.message}</span>
        <ul>
          {status.changes.map((c) => (
            <li key={`${c.kind}-${c.skill_id}`}>
              {t(`replan.change.${c.kind}`)}: {c.skill_id}. {c.detail}
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
  const [result, status] = await Promise.all([fetchPathway(roleId, scenario, snapshotDate), fetchPlanStatus()]);
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
      {d("continue")} <ArrowUpRight size={15} aria-hidden />
    </Link>
  ) : savedHere ? (
    <span className="a-chip" data-tone="up">
      <Check size={13} aria-hidden /> {t("plan.saved", { date: savedHere.saved_at.slice(0, 10) })}
    </span>
  ) : (
    <ActionForm action={savePlanAction} fields={{ role_id: roleId, scenario }} label={t("plan.save")} className="a-inline-form" />
  );

  return (
    <div className="a-stack" style={{ gap: 24 }}>
      <PageHeader
        eyebrow={d("curriculum")}
        title={plan.role_label || plan.role_id}
        description={`${t("totalWeeks", { weeks: plan.total_weeks })} · ${d("pathBody")}`}
        actions={action}
      >
        <MetaBar meta={plan.meta} />
      </PageHeader>
      {!savedHere && !snapshotDate ? <p className="a-small a-muted" style={{ margin: "-12px 0 0" }}>{t("plan.decide")}</p> : null}
      {status.ok && savedHere ? <ReplanBanner status={status.data} /> : null}
      <Summary plan={plan} />

      <nav className="a-toolbar" aria-label={d("options")}>
        <Link href={`/app/progress${query}`} className="a-tool">
          <Target size={16} aria-hidden /> {t("plan.progressLink")}
        </Link>
        <Link href={`/app/sdg${query}`} className="a-tool">
          <Leaf size={16} aria-hidden /> {t("plan.sdgLink")}
        </Link>
        <Link href={`/app/courses${query}`} className="a-tool">
          <BookOpen size={16} aria-hidden /> {t("catalogue.browse")}
        </Link>
        <Link href={`/app/pathway/compare${query}`} className="a-tool">
          <GitCompareArrows size={16} aria-hidden /> {t("compare.link")}
        </Link>
      </nav>

      <PathwaySteps steps={plan.steps} />
      {(plan.unmet ?? []).length > 0 ? (
        <section className="a-card">
          <div className="a-card-head">
            <h2>{t("unmet.title")}</h2>
          </div>
          <div className="a-card-body">
            {(plan.unmet ?? []).map((u) => (
              <div key={u.skill_id} className="a-unmet">
                <strong>{u.label}</strong> <span className="a-chip" data-tone="warn">{t(`unmet.${u.reason}`)}</span>
                <p className="a-small a-muted">{u.detail}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
