import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Heatmap } from "@/components/viz";
import type { ScenarioId } from "@/lib/api";

import { fetchGaps } from "../api";
import { heatRows, topGapSkills } from "./OrgDashboardView";

/** Team skills-gap heatmap: rows = target roles, columns = the skills the team lacks most. */
export async function GapsView({ scenario }: { scenario: ScenarioId }) {
  const t = await getTranslations("ui.org");
  const tn = await getTranslations("ui.nav");
  const result = await fetchGaps(scenario);
  if (!result.ok) return <ErrorState failure={result} />;
  const skills = topGapSkills(result.data, 14);
  return (
    <div className="a-stack">
      <div className="a-pagehead">
        <h1 className="a-h1">{t("gapsTitle")}</h1>
      </div>
      <section className="a-card">
        {skills.length ? (
          <Heatmap
            rows={heatRows(result.data, skills)}
            columns={skills.map((s) => ({ id: s.id, label: s.label }))}
            legend={[t("gapsLow"), t("gapsHigh")]}
          />
        ) : (
          <p className="a-muted">{t("noGaps")}</p>
        )}
      </section>
      <div className="a-chips">
        {result.data.role_ids.map((r) => (
          <Link key={r} className="a-btn is-ghost is-small" href={`/org/plan?role=${encodeURIComponent(r)}&scenario=${scenario}`}>
            {tn("teamPlan")}: {result.data.role_labels?.[r] ?? r}
          </Link>
        ))}
      </div>
      <MetaBar meta={result.data.meta} />
    </div>
  );
}
