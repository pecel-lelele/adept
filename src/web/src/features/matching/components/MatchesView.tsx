import { ArrowRight, CircleDashed, Circle } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { HistoricalSnapshotBanner } from "@/components/HistoricalSnapshotBanner";
import { scoreColour, SdgTiles } from "@/components/viz";
import { fetchJobsSummary } from "@/features/jobs";
import { fetchRadar } from "@/features/trends/api";
import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchMatches, fetchReplay } from "../api";
import { ReplayChanges } from "./ReplayChanges";
import { SdgWeightSlider } from "./SdgWeightSlider";
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

/** Share of the role's required skill levels the person already holds (the overlap part). */
export const READY_OVERLAP = 0.5;

function overlapOf(m: Schemas["RoleMatch"]): number {
  return m.components.find((c) => c.name === "skill_overlap")?.value ?? 0;
}

/**
 * Step 3: ranked future roles. Ranking options first, then one card per role: rank, name and
 * fit; what drives the score, which skills are missing, which goals the role serves; actions.
 */
export async function MatchesView({
  scenario,
  snapshotDate,
  sdgWeight = 0,
}: {
  scenario: ScenarioId;
  snapshotDate?: string;
  sdgWeight?: number;
}) {
  const t = await getTranslations("matching");
  const th = await getTranslations("ui.home");
  const tp = await getTranslations("ui.page");
  const [result, radar, changes, jobs] = await Promise.all([
    fetchMatches(scenario, snapshotDate, sdgWeight),
    fetchRadar(scenario),
    snapshotDate ? fetchReplay(scenario, snapshotDate, sdgWeight) : Promise.resolve(null),
    fetchJobsSummary(scenario),
  ]);
  const tj = await getTranslations("jobs");
  const openings = new Map(jobs.ok ? jobs.data.roles.map((r) => [r.role_id, r.open_count]) : []);
  const labels = await componentLabels();
  // The detail page must explain the same ranking: carry the snapshot and the UN Goals weight.
  const replay =
    (snapshotDate ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : "") +
    (sdgWeight > 0 ? `&sdg=${sdgWeight.toFixed(2)}` : "");

  return (
    <div className="a-view">
      <PageHeader eyebrow={tp("stepOf", { step: 3 })} title={t("title")} description={t("description")}>
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      <HistoricalSnapshotBanner date={snapshotDate} latestHref={`/app/matches?scenario=${scenario}${sdgWeight > 0 ? `&sdg=${sdgWeight.toFixed(2)}` : ""}`} />

      <section className="a-card a-controls" aria-label={tp("rankingOptions")}>
        {radar.ok ? (
          <SnapshotPicker
            dates={radar.data.meta.available_snapshots}
            value={snapshotDate ?? ""}
            latestLabel={th("latest")}
            label={t("snapshotDate")}
          />
        ) : null}
        <SdgWeightSlider value={sdgWeight} label={t("sdgWeight")} hint={t("sdgWeightHint")} offLabel={t("sdgWeightOff")} />
      </section>

      {changes?.ok ? <ReplayChanges data={changes.data} /> : null}
      {!result.ok ? (
        <ErrorState failure={result} />
      ) : (
        <>
          {(
            [
              ["ready", result.data.matches.filter((m) => overlapOf(m) >= READY_OVERLAP)],
              ["explore", result.data.matches.filter((m) => overlapOf(m) < READY_OVERLAP)],
            ] as const
          ).map(([group, matches]) =>
            matches.length ? (
              <section key={group} className="a-stack" aria-labelledby={`matches-${group}`}>
                <header className="a-section-head">
                  <h2 id={`matches-${group}`}>{t(group === "ready" ? "readyNow" : "worthExploring")}</h2>
                  <p className="a-muted a-small">
                    {t(group === "ready" ? "readyNowHint" : "worthExploringHint", {
                      share: Math.round(READY_OVERLAP * 100),
                    })}
                  </p>
                </header>
          <ol className="a-rolecards">
            {matches.map((m) => {
              const i = result.data.matches.indexOf(m);
              const goals = [...new Map(m.sdg_targets.map((s) => [s.goal, { goal: s.goal, title: s.label }])).values()];
              const pct = Math.round(m.score * 100);
              const detail = `/app/matches/${encodeURIComponent(m.role_id)}?scenario=${scenario}${replay}`;
              return (
                <li key={m.role_id}>
                  <article className="a-card a-rolecard" data-top={i === 0 || undefined}>
                    <header className="a-rolecard-head">
                      <span className="a-rank-num">{i + 1}</span>
                      <div className="a-rolecard-title">
                        {i === 0 ? <span className="a-eyebrow">{tp("bestFit")}</span> : null}
                        <h2>
                          <Link href={detail}>{m.label}</Link>
                        </h2>
                        <span className="a-chips">
                          <span className="a-chip" data-tone={m.missing_skills.length ? "down" : "up"}>
                            {tp("toLearn", { count: m.missing_skills.length })}
                          </span>
                          <span className="a-chip" data-tone={m.partial_skills.length ? "warn" : "up"}>
                            {tp("toImprove", { count: m.partial_skills.length })}
                          </span>
                          {openings.get(m.role_id) ? (
                            <Link className="a-chip" data-tone="dark" href={`/app/jobs?role=${encodeURIComponent(m.role_id)}&scenario=${scenario}`}>
                              {tj("openingsChip", { count: openings.get(m.role_id) ?? 0 })}
                            </Link>
                          ) : null}
                        </span>
                      </div>
                      <div className="a-fit" style={{ color: scoreColour(m.score) }}>
                        <strong>{pct}%</strong>
                        <small>{tp("fit")}</small>
                        <span className="a-fit-track" aria-hidden>
                          <i style={{ width: `${pct}%`, background: scoreColour(m.score) }} />
                        </span>
                      </div>
                    </header>
                    <div className="a-rolecard-body">
                      <div>
                        <h3>{tp("drivers")}</h3>
                        <ScoreParts parts={m.components} labels={labels} />
                      </div>
                      <div>
                        <h3>{tp("gapTitle")}</h3>
                        {m.missing_skills.length || m.partial_skills.length ? (
                          <ul className="a-gaplist">
                            {m.missing_skills.slice(0, 4).map((s) => (
                              <li key={s.id}>
                                <Circle size={11} aria-hidden data-tone="down" /> {s.label}
                              </li>
                            ))}
                            {m.partial_skills.slice(0, Math.max(0, 4 - m.missing_skills.length)).map((s) => (
                              <li key={s.id}>
                                <CircleDashed size={11} aria-hidden data-tone="warn" /> {s.label}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="a-muted a-small">{tp("noGap")}</p>
                        )}
                      </div>
                      <div>
                        <h3>{tp("goals")}</h3>
                        {goals.length ? <SdgTiles goals={goals.slice(0, 4)} /> : <p className="a-muted a-small">—</p>}
                      </div>
                    </div>
                    <footer className="a-rolecard-foot">
                      <Link className="a-btn is-ghost is-small" href={detail}>
                        {t("viewDetail")}
                      </Link>
                      <Link
                        className="a-btn is-small"
                        href={`/app/pathway?role=${encodeURIComponent(m.role_id)}&scenario=${scenario}`}
                      >
                        {t(snapshotDate ? "viewLatestPathway" : "viewPathway")} <ArrowRight size={14} aria-hidden />
                      </Link>
                    </footer>
                  </article>
                </li>
              );
            })}
          </ol>
              </section>
            ) : null,
          )}
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
