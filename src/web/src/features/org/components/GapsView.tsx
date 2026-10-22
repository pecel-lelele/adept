import { ArrowRight, Grid3x3, Layers, Target } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Kpis, MetaBar, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Heatmap } from "@/components/viz";
import type { ScenarioId } from "@/lib/api";

import { fetchGaps } from "../api";
import { heatRows, topGapSkills } from "./OrgDashboardView";

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
  const byRole = data.role_ids
    .map((r) => {
      const cells = data.cells.filter((c) => c.role_id === r);
      const avg = cells.length ? cells.reduce((s, c) => s + c.gap, 0) / cells.length : 0;
      return { id: r, label: data.role_labels?.[r] ?? r, avg };
    })
    .sort((a, b) => b.avg - a.avg);
  const biggest = byRole[0];

  return (
    <div className="a-view">
      <PageHeader eyebrow={tp("stepOf", { step: 3 })} title={t("gapsTitle")} description={tp("gapsDesc")}>
        <MetaBar meta={data.meta} />
      </PageHeader>
      <Kpis
        items={[
          { label: tp("kRolesCompared"), value: data.role_ids.length, icon: <Target size={15} /> },
          { label: tp("kSkillsWithGap"), value: skills.length, icon: <Layers size={15} /> },
          {
            label: tp("kBiggestGap"),
            value: biggest ? `${Math.round(biggest.avg * 100)}%` : "—",
            icon: <Grid3x3 size={15} />,
            tone: biggest && biggest.avg > 0.5 ? "warn" : undefined,
            note: biggest?.label,
          },
        ]}
      />
      <section className="a-card" aria-labelledby="h-heat">
        <div className="a-card-head">
          <h2 id="h-heat">
            <Grid3x3 size={16} aria-hidden /> {tp("heatTitle")}
          </h2>
        </div>
        {skills.length ? (
          <Heatmap
            rows={heatRows(data, skills)}
            columns={skills.map((s) => ({ id: s.id, label: s.label }))}
            legend={[t("gapsLow"), t("gapsHigh")]}
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
                <span className="a-rank-num">{i + 1}</span>
                <span className="a-rank-main">
                  <strong>{r.label}</strong>
                  <small className="a-inline">
                    {tn("teamPlan")} <ArrowRight size={12} aria-hidden />
                  </small>
                </span>
                <span className="a-scorebar" role="img" aria-label={`${Math.round(r.avg * 100)}%`}>
                  <strong>{Math.round(r.avg * 100)}%</strong>
                  <span className="a-scorebar-track" aria-hidden>
                    <span style={{ width: `${Math.round(r.avg * 100)}%`, background: "var(--a-down)" }} />
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
