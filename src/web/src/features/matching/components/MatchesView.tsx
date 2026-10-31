import { CircleDashed, Circle } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { EmptyState, MetaBar, PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { HistoricalSnapshotBanner } from "@/components/HistoricalSnapshotBanner";
import { scoreColour } from "@/components/viz";
import { fetchJobsSummary } from "@/features/jobs";
import { Fold } from "@/components/Fold";
import type { ScenarioId, Schemas } from "@/lib/api";
import { savePlanAction } from "@/features/pathway/actions";
import { fetchPlanStatus } from "@/features/pathway/api";
import { ActionForm } from "@/features/pathway/components/ActionForm";

import { fetchMatches, fetchReplay } from "../api";
import { ReplayChanges } from "./ReplayChanges";
import { SdgWeightSlider } from "./SdgWeightSlider";
import { SnapshotPicker } from "./SnapshotPicker";
import { MatchImprovements } from "./MatchImprovements";
import { MatchSdgTargets } from "./MatchSdgTargets";
import { ProfileNote } from "./ProfileNote";

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
  chooseRoleFirst = false,
}: {
  scenario: ScenarioId;
  snapshotDate?: string;
  sdgWeight?: number;
  chooseRoleFirst?: boolean;
}) {
  const t = await getTranslations("matching");
  const th = await getTranslations("ui.home");
  const tp = await getTranslations("ui.page");
  const [result, changes, jobs, status] = await Promise.all([
    fetchMatches(scenario, snapshotDate, sdgWeight),
    snapshotDate ? fetchReplay(scenario, snapshotDate, sdgWeight) : Promise.resolve(null),
    fetchJobsSummary(scenario),
    fetchPlanStatus(),
  ]);
  // Choosing again would silently replace the saved plan and skip re-plan review,
  // so offer no choice until the saved plan is known.
  const saved = status.ok ? status.data.saved : null;
  const planKnown = status.ok;
  const tj = await getTranslations("jobs");
  const openings = new Map(jobs.ok ? jobs.data.roles.map((r) => [r.role_id, r.open_count]) : []);
  // The detail page must explain the same ranking: carry the snapshot and the UN Goals weight.
  const replay =
    (snapshotDate ? `&snapshot_date=${encodeURIComponent(snapshotDate)}` : "") +
    (sdgWeight > 0 ? `&sdg=${sdgWeight.toFixed(2)}` : "");

  return (
    <div className="a-view">
      <PageHeader title={t("title")} description={t("description")}>
        {result.ok ? <MetaBar meta={result.data.meta} /> : null}
      </PageHeader>
      {chooseRoleFirst ? <p className="a-notice" role="status">{t("chooseRoleFirst")}</p> : null}
      <HistoricalSnapshotBanner date={snapshotDate} latestHref={`/app/matches?scenario=${scenario}${sdgWeight > 0 ? `&sdg=${sdgWeight.toFixed(2)}` : ""}`} />

      <section className="a-card a-controls" aria-label={tp("rankingOptions")}>
        {result.ok ? (
          <SnapshotPicker
            dates={result.data.meta.available_snapshots ?? []}
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
          <ProfileNote note={result.data.matches[0]?.profile_note} />
          {result.data.matches.length === 0 ? (
            <EmptyState title={t("emptyTitle")} description={t("emptyHint")} action={
              <Link className="a-btn is-small" href="/app/profile">{tp("jSkills")}</Link>
            } />
          ) : null}
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
              const pct = (m.score * 100).toFixed(1);
              const buildCount = m.missing_skills.length + m.partial_skills.length;
              const detail = `/app/matches/${encodeURIComponent(m.role_id)}?scenario=${scenario}${replay}`;
              const card = (
                  <article className="a-card a-rolecard" data-top={i === 0 || undefined}>
                    <header className="a-rolecard-head">
                      <span className="a-rank-num">{i + 1}</span>
                      <div className="a-rolecard-title">
                        {i === 0 ? <span className="a-eyebrow">{tp("bestFit")}</span> : null}
                        <h2>
                          <Link href={detail}>{m.label}</Link>
                        </h2>
                        <p className="a-rolecard-meta">
                          {saved?.role_id === m.role_id ? <span className="a-chip" data-tone="up">{t("currentTarget")}</span> : null}
                          {buildCount ? <span>{t("skillsToBuild", { count: buildCount })}</span> : <span>{tp("noGap")}</span>}
                          {openings.get(m.role_id) ? (
                            <Link href={`/app/jobs?role=${encodeURIComponent(m.role_id)}&scenario=${scenario}`}>
                              {tj("openingsChip", { count: openings.get(m.role_id) ?? 0 })}
                            </Link>
                          ) : null}
                        </p>
                      </div>
                      <div className="a-fit" style={{ color: scoreColour(m.score) }} role="img" aria-label={`${pct}% ${tp("fit")}`}>
                        <strong>{pct}%</strong>
                        <span className="a-fit-track" aria-hidden>
                          <i style={{ width: `${pct}%`, background: scoreColour(m.score) }} />
                        </span>
                      </div>
                    </header>
                    <div className="a-rolecard-body">
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
                        {m.sdg_targets.length ? <MatchSdgTargets targets={m.sdg_targets} /> : <p className="a-muted a-small">—</p>}
                      </div>
                    </div>
                    <MatchImprovements items={m.improvements ?? []} />
                    <footer className="a-rolecard-foot">
                      {saved?.role_id === m.role_id ? (
                        <Link className="a-btn is-small" href={`/app/pathway?role=${encodeURIComponent(m.role_id)}&scenario=${saved.scenario}`}>
                          {t("openPlan")}
                        </Link>
                      ) : planKnown ? (
                        <ActionForm action={savePlanAction} fields={{ role_id: m.role_id, scenario }} label={t("chooseRole")} className="a-inline-form" />
                      ) : (
                        <p className="a-muted a-small" role="status">{t("planStatusUnavailable")}</p>
                      )}
                    </footer>
                  </article>
              );
              return (
                <li key={m.role_id}>
                  {i < 3 ? card : (
                    <Fold title={`${i + 1}. ${m.label}`} meta={<span className="a-inline">{pct}%</span>}>
                      {card}
                    </Fold>
                  )}
                </li>
              );
            })}
          </ol>
              </section>
            ) : null,
          )}
        </>
      )}
    </div>
  );
}
