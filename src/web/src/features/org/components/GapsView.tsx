import { ArrowRight, Grid3x3, Layers, Target } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Kpis, MetaBar, PageHeader } from "@/components";
import { journeyStepCount, orgWorkspace } from "@/config/navigation";
import { ErrorState } from "@/components/ErrorState";
import { Heatmap } from "@/components/viz";
import type { ScenarioId } from "@/lib/api";

import { fetchGaps } from "../api";
import { heatRows, topGapSkills } from "./OrgDashboardView";
import { TeamLearningProgress } from "./TeamLearningProgress";

/**
 * Step 3 for organisations: the team skills-gap heatmap (rows = target roles, columns = the
 * skills the team lacks most), then each role's average gap with a link to its team plan.
 */
export async function GapsView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const tp = await getTranslations("ui.page");
  const result = await fetchGaps(scenario);
  if (!result.ok) return <ErrorState failure={result} />;
  const data = result.data;
  const skills = topGapSkills(data, 14);
  // Average over each role's required skills only (from the API, the same figure that picks
  // the default team target); zero cells for skills a role does not need are not averaged.
  const byRole = data.role_ids
    .map((r) => ({ id: r, label: data.role_labels?.[r] ?? r, avg: data.role_gaps?.[r] ?? null, suppressed: data.role_suppressed?.[r] ?? false }))
    .sort((a, b) => (b.avg ?? -1) - (a.avg ?? -1) || b.id.localeCompare(a.id)); // same tie-break as the backend
  const biggest = byRole[0];

  return (
    <div className="a-view">
      <PageHeader eyebrow={tp("stepOf", { step: 3, total: journeyStepCount(orgWorkspace) })} title={t("gapsTitle")} description={tp("gapsDesc")}>
        <MetaBar meta={data.meta} />
      </PageHeader>
      <Kpis
        items={[
          { label: tp("kRolesCompared"), value: data.role_ids.length, icon: <Target size={15} /> },
          { label: tp("kSkillsWithGap"), value: data.cells.some((c) => c.suppressed) ? "—" : skills.length, icon: <Layers size={15} /> },
          {
            label: tp("kBiggestGap"),
            value: biggest?.avg != null ? `${Math.round(biggest.avg * 100)}%` : "—",
            icon: <Grid3x3 size={15} />,
            tone: biggest?.avg != null && biggest.avg > 0.5 ? "warn" : undefined,
            note: biggest?.avg != null ? biggest.label : undefined,
          },
        ]}
      />
      <section className="a-card" aria-labelledby="h-heat">
        <div className="a-card-head">
          <h2 id="h-heat">
            <Grid3x3 size={16} aria-hidden /> {tp("heatTitle")}
          </h2>
        </div>
        {Object.values(data.role_suppressed ?? {}).some(Boolean) ? <p className="a-muted" role="status">{t("tooFewMembers")}</p> : null}
        {skills.length ? (
          <Heatmap
            rows={heatRows(data, skills)}
            columns={skills.map((s) => ({ id: s.id, label: s.label }))}
            legend={[t("gapsLow"), t("gapsHigh")]}
            suppressedLabel={t("tooFewMembers")}
          />
        ) : (
          <p className="a-muted">{t("noGaps")}</p>
        )}
      </section>
      <section className="a-card a-flush" aria-labelledby="h-byrole">
        <div className="a-card-head a-pad">
          <h2 id="h-byrole">{tp("gapByRole")}</h2>
        </div>
        <ol className="a-rank a-pad" style={{ paddingBottom: 12 }}>
          {byRole.map((r, i) => (
            <li key={r.id}>
              <Link href={`/org/plan?role=${encodeURIComponent(r.id)}&scenario=${scenario}`}>
                <span className="a-rank-num">{r.suppressed ? "—" : i + 1}</span>
                <span className="a-rank-main">
                  <strong>{r.label}</strong>
                  <small className="a-inline">
                    {tn("teamPlan")} <ArrowRight size={12} aria-hidden />
                  </small>
                </span>
                {r.suppressed || r.avg == null ? <span className="a-muted a-small">{t("tooFewMembers")}</span> : <span className="a-scorebar" role="img" aria-label={`${Math.round(r.avg * 100)}%`}>
                  <strong>{Math.round(r.avg * 100)}%</strong>
                  <span className="a-scorebar-track" aria-hidden>
                    <span style={{ width: `${Math.round(r.avg * 100)}%`, background: "var(--a-down)" }} />
                  </span>
                </span>}
              </Link>
            </li>
          ))}
        </ol>
      </section>
      <TeamLearningProgress rows={data.learning_progress ?? []} />
    </div>
  );
}
