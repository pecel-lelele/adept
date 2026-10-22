import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Ring, Scene3D, scoreColour, SdgTiles } from "@/components/viz";
import { fetchRadar } from "@/features/trends/api";
import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchMatches } from "../api";
import { componentLabels } from "./labels";
import { SnapshotPicker } from "./SnapshotPicker";

/** One horizontal bar per score part: how much each part contributed to the fit. */
function ScoreParts({ parts, labels }: { parts: Schemas["ScoreComponent"][]; labels: Record<string, string> }) {
  return (
    <div className="a-bars">
      {parts.map((c) => (
        <div className="a-bar a-bar-plain" key={c.name} title={c.explanation}>
          <span className="a-bar-label">{labels[c.name] ?? c.name.replaceAll("_", " ")}</span>
          <span className="a-bar-track">
            <span className="a-bar-fill" style={{ width: `${Math.round(c.value * 100)}%`, opacity: c.provided ? 1 : 0.35 }} />
          </span>
          <span className="a-bar-value">{Math.round(c.value * 100)}%</span>
        </div>
      ))}
    </div>
  );
}

/** Step 3: ranked future roles. Each card: fit ring, what drives it, the gap, the goals. */
export async function MatchesView({ scenario, snapshotDate }: { scenario: ScenarioId; snapshotDate?: string }) {
  const t = await getTranslations("matching");
  const th = await getTranslations("ui.home");
  const [result, radar] = await Promise.all([fetchMatches(scenario, snapshotDate), fetchRadar(scenario)]);
  const labels = await componentLabels();
  const replay = snapshotDate ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : "";

  return (
    <div className="a-stack">
      <section className="a-hero" style={{ minHeight: 0 }}>
        <div>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
          {radar.ok ? (
            <SnapshotPicker
              dates={radar.data.meta.available_snapshots}
              value={snapshotDate ?? ""}
              latestLabel={th("latest")}
              label={t("snapshotDate")}
            />
          ) : null}
        </div>
        <Scene3D variant="cards" />
      </section>
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <>
          <div className="a-stack">
            {result.data.matches.map((m, i) => {
              const goals = [...new Map(m.sdg_targets.map((s) => [s.goal, { goal: s.goal, title: s.label }])).values()];
              const gaps = m.missing_skills.length + m.partial_skills.length;
              return (
                <article className="a-card" key={m.role_id}>
                  <div className="a-grid" style={{ alignItems: "center" }}>
                    <div className="a-span-4" style={{ display: "flex", gap: 16, alignItems: "center" }}>
                      <Ring value={m.score} size={92} stroke={9} caption={th("fit")} colour={scoreColour(m.score)} />
                      <div>
                        <span className="a-eyebrow">#{i + 1}</span>
                        <h2 style={{ margin: "2px 0 8px", fontSize: 19, letterSpacing: -0.4 }}>{m.label}</h2>
                        <span className="a-chip" data-tone={gaps ? "warn" : "up"}>
                          {th("gaps", { count: gaps })}
                        </span>
                      </div>
                    </div>
                    <div className="a-span-5">
                      <ScoreParts parts={m.components} labels={labels} />
                    </div>
                    <div className="a-span-3 a-stack" style={{ gap: 10, justifyItems: "start" }}>
                      {goals.length ? <SdgTiles goals={goals.slice(0, 4)} /> : null}
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <Link className="a-btn is-ghost is-small" href={`/app/matches/${encodeURIComponent(m.role_id)}?scenario=${scenario}${replay}`}>
                          {t("viewDetail")}
                        </Link>
                        <Link className="a-btn is-small" href={`/app/pathway?role=${encodeURIComponent(m.role_id)}&scenario=${scenario}`}>
                          {t(snapshotDate ? "viewLatestPathway" : "viewPathway")} <ArrowRight size={14} aria-hidden />
                        </Link>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          <MetaBar meta={result.data.meta} />
          {result.data.data_provenance_note ? (
            <p className="a-small a-muted">
              {t("provenance")}: {result.data.data_provenance_note}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
