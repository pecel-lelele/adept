import { ArrowRight, Check, CircleDashed, Circle } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar, ScoreBreakdown } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Ring, scoreColour, SdgTiles } from "@/components/viz";
import { RoleOutlookPanel } from "@/features/scenarios/components/RoleOutlookPanel";
import type { ScenarioId } from "@/lib/api";

import { fetchMatch } from "../api";
import { componentLabels } from "./labels";

/** One role: fit ring and next action first, then why (score parts), the gap, the outlook. */
export async function MatchDetailView({
  roleId,
  scenario,
  snapshotDate,
}: {
  roleId: string;
  scenario: ScenarioId;
  snapshotDate?: string;
}) {
  const t = await getTranslations("matching");
  const th = await getTranslations("ui.home");
  const result = await fetchMatch(roleId, scenario, snapshotDate);
  if (!result.ok) return <ErrorState failure={result} />;
  const m = result.data;
  const goals = [...new Map(m.sdg_targets.map((s) => [s.goal, { goal: s.goal, title: `${s.target} ${s.label}` }])).values()];

  return (
    <div className="a-stack">
      <section className="a-hero" style={{ minHeight: 0 }}>
        <div>
          <h1>{m.label}</h1>
          <div className="a-hero-actions">
            <Link className="a-btn" href={`/app/pathway?role=${encodeURIComponent(m.role_id)}&scenario=${scenario}`}>
              {t(snapshotDate ? "viewLatestPathway" : "viewPathway")} <ArrowRight size={16} aria-hidden />
            </Link>
            <Link className="a-btn is-ghost" href={`/app/pathway/compare?scenario=${scenario}&role_ids=${encodeURIComponent(m.role_id)}`}>
              {th("compare")}
            </Link>
          </div>
        </div>
        <div style={{ display: "grid", placeItems: "center" }}>
          <Ring value={m.score} size={150} stroke={13} caption={th("fit")} colour={scoreColour(m.score)} />
        </div>
      </section>
      <div className="a-grid">
        <section className="a-card a-span-7">
          <div className="a-card-head">
            <h2>{t("breakdown")}</h2>
          </div>
          <ScoreBreakdown score={m.score} components={m.components} labels={await componentLabels()} />
        </section>
        <section className="a-card a-span-5">
          <div className="a-card-head">
            <h2>{t("missing")} · {t("partial")}</h2>
          </div>
          <ul className="a-stack" style={{ gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
            {m.missing_skills.map((s) => (
              <li key={s.id} className="a-chip" data-tone="down" style={{ justifyContent: "flex-start" }}>
                <Circle size={12} aria-hidden /> {s.label}
              </li>
            ))}
            {m.partial_skills.map((s) => (
              <li key={s.id} className="a-chip" data-tone="warn" style={{ justifyContent: "flex-start" }}>
                <CircleDashed size={12} aria-hidden /> {s.label}
              </li>
            ))}
            {!m.missing_skills.length && !m.partial_skills.length ? (
              <li className="a-chip" data-tone="up">
                <Check size={12} aria-hidden /> —
              </li>
            ) : null}
          </ul>
          {goals.length ? (
            <div style={{ marginTop: 18 }}>
              <SdgTiles goals={goals} />
            </div>
          ) : null}
        </section>
        <div className="a-span-12">
          <RoleOutlookPanel roleId={m.role_id} scenario={scenario} />
        </div>
      </div>
      <MetaBar meta={m.meta} />
      {m.data_provenance_note ? (
        <p className="a-small a-muted">
          {t("provenance")}: {m.data_provenance_note}
        </p>
      ) : null}
    </div>
  );
}
