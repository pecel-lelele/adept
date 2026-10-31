import { Bot, Minus, Radar, TrendingDown, TrendingUp } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { EstimateLabel, Kpis, MetaBar, PageHeader, TrendPill } from "@/components";
import { journeyStepCount } from "@/config/navigation";
import { ErrorState } from "@/components/ErrorState";
import { TrendBars } from "@/components/viz";
import { fetchMyProfile } from "@/features/profile/api";
import { SnapshotPicker } from "@/components/SnapshotPicker";
import type { ScenarioId } from "@/lib/api";

import { fetchCompare, fetchRadar, fetchRoleDirections } from "../api";
import { DEFAULT_HORIZON, DEFAULT_PRESET, KIND_OF_VIEW, type TrendRange } from "../range";
import { SignalExplorer } from "./SignalExplorer";
import { RoleDirectionsCard } from "./RoleDirectionsCard";
import { TrendRangeCard } from "./TrendRangeCard";
import "./radar.css";
import { MalaysiaContextCard } from "./MalaysiaContextCard";

/**
 * Step 2, the Future Skills Radar. Hierarchy: how many skills rise / hold / decline → the
 * strongest movers as a labelled diverging chart, beside the learner's own skills (or, for
 * an organisation, the skills most exposed to automation) → every tracked skill, searchable.
 */
export async function RadarView({
  scenario,
  snapshotDate,
  context = "individual",
  range = { view: "skills", preset: DEFAULT_PRESET, entities: [], mode: "indexed", horizon: DEFAULT_HORIZON },
}: {
  scenario: ScenarioId;
  snapshotDate?: string;
  context?: "individual" | "organisation";
  /** Trend over time: every choice comes from the URL (see `parseTrendRange`). */
  range?: TrendRange;
}) {
  const t = await getTranslations("trends");
  const d = await getTranslations("common.design");
  const tp = await getTranslations("ui.page");
  const th = await getTranslations("ui.home");
  const tf = await getTranslations("common.freshness");
  const compare = (chosen: TrendRange) =>
    fetchCompare({ kind: KIND_OF_VIEW[chosen.view], entities: chosen.entities, preset: chosen.preset, start: chosen.from, end: chosen.to, scenario, horizon: chosen.horizon, mode: chosen.mode });
  const [result, profile, series] = await Promise.all([
    fetchRadar(scenario, snapshotDate),
    context === "individual" ? fetchMyProfile() : Promise.resolve(null),
    compare(range),
  ]);
  // A rejected date or line choice (422) falls back to this view's movers, so the form and its
  // reset stay usable and the card explains what was refused.
  const rejected = !series.ok && series.status === 422;
  const shownRange: TrendRange = rejected ? { ...range, preset: DEFAULT_PRESET, from: undefined, to: undefined, entities: [] } : range;
  const rangeSeries = rejected ? await compare(shownRange) : series;
  if (!result.ok) return (
    <div className="a-view a-radar-view">
      <PageHeader eyebrow={context === "organisation" ? tp("radarEyebrowOrg") : tp("stepOf", { step: 2, total: journeyStepCount() })}
        title={context === "organisation" ? t("orgTitle") : t("title")} description={tp("radarDesc")}>
        <EstimateLabel scenario={scenario} />
        {snapshotDate ? <span className="a-chip">{tp("asOf", { date: snapshotDate })}</span> : null}
      </PageHeader>
      <ErrorState failure={result} />
      {snapshotDate ? (
        <a className="a-btn is-ghost" href={`${context === "organisation" ? "/org/radar" : "/app/radar"}?scenario=${scenario}`}>
          {tf("backToLatest")}
        </a>
      ) : null}
    </div>
  );
  const { items, meta } = result.data;
  const directions = await fetchRoleDirections(scenario, meta.snapshot_date);
  const v = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const dir = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const count = (x: string) => items.filter((i) => i[dir] === x).length;
  const sorted = [...items].sort((a, b) => b[v] - a[v]);
  const movers = [...sorted.slice(0, 6), ...sorted.slice(-6).filter((i) => i[v] < 0)]
    .filter((i, n, all) => all.findIndex((x) => x.skill_id === i.skill_id) === n)
    .map((i) => ({ id: i.skill_id, label: i.skill_label, value: i[v], direction: i[dir] }));
  const byId = new Map(items.map((i) => [i.skill_id, i]));
  const mine = profile?.ok
    ? profile.data.skills
        .map((s) => ({ id: s.skill_id, item: byId.get(s.skill_id) }))
        .sort((a, b) => (b.item?.[v] ?? -99) - (a.item?.[v] ?? -99))
    : [];
  const exposed = [...items].sort((a, b) => b.automation_exposure - a.automation_exposure).slice(0, 8);

  return (
    <div className="a-view a-radar-view">
      <PageHeader
        eyebrow={context === "organisation" ? tp("radarEyebrowOrg") : tp("stepOf", { step: 2, total: journeyStepCount() })}
        title={context === "organisation" ? t("orgTitle") : t("title")}
        description={tp("radarDesc")}
        actions={
          <div className="a-radar-edition">
            <SnapshotPicker dates={meta.available_snapshots} value={snapshotDate ?? ""}
              latestLabel={th("latest")} label={t("range.pageDateLabel")} />
            <p className="a-small a-muted">{t("range.pageDateHint")}</p>
          </div>
        }
      >
        <MetaBar meta={meta} />
      </PageHeader>
      {meta.is_replay !== true && meta.observed_to && Date.parse(meta.snapshot_date) - Date.parse(meta.observed_to) > 60 * 864e5 ? (
        <p className="a-notice" role="note">
          {tp("historical", { from: meta.observed_from ?? meta.observed_to, to: meta.observed_to, date: meta.snapshot_date })}
        </p>
      ) : null}

      <Kpis
        items={[
          { label: d("rising"), value: count("rising"), icon: <TrendingUp size={15} />, tone: "up", note: tp("risingNote") },
          { label: d("stable"), value: count("stable"), icon: <Minus size={15} />, note: tp("stableNote") },
          { label: d("declining"), value: count("declining"), icon: <TrendingDown size={15} />, tone: "down", note: tp("decliningNote") },
          {
            label: tp("kTracked"),
            value: items.length,
            icon: <Radar size={15} />,
            note: meta.observed_from && meta.observed_to
              ? d("observed", { from: meta.observed_from, to: meta.observed_to })
              : tp("asOf", { date: meta.snapshot_date }),
          },
        ]}
      />

      <div className="a-split">
        <section className="a-card" aria-labelledby="h-movers">
          <div className="a-card-head">
            <h2 id="h-movers">{tp("movers")}</h2>
          </div>
          <p className="a-card-sub">{tp("moversHint")}</p>
          <TrendBars items={movers} axis={{ down: d("declining"), up: d("rising") }} />
        </section>

        {context === "individual" ? (
          <section className="a-card" aria-labelledby="h-mine">
            <div className="a-card-head">
              <h2 id="h-mine">{tp("yourSkills")}</h2>
            </div>
            {mine.length ? (
              <ul className="a-mini">
                {mine.map(({ id, item }) => (
                  <li key={id}>
                    <span>{item?.skill_label ?? id}</span>
                    <TrendPill direction={item?.[dir]} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="a-muted a-small">{tp("yourSkillsNone")}</p>
            )}
          </section>
        ) : (
          <section className="a-card" aria-labelledby="h-exposed">
            <div className="a-card-head">
              <h2 id="h-exposed">
                <Bot size={16} aria-hidden /> {tp("exposed")}
              </h2>
            </div>
            <p className="a-card-sub">{tp("exposedHint")}</p>
            <ul className="a-mini">
              {exposed.map((i) => (
                <li key={i.skill_id}>
                  <span>{i.skill_label}</span>
                  <b title={tp("exposureScoreHint")}>{i.automation_exposure.toFixed(2)}</b>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {rangeSeries.ok ? (
        <TrendRangeCard
          data={rangeSeries.data}
          range={shownRange}
          rejected={rejected}
          scenario={scenario}
          snapshotDate={snapshotDate}
          pathname={context === "organisation" ? "/org/radar" : "/app/radar"}
        />
      ) : (
        <>
          <ErrorState failure={rangeSeries} />
          {rejected ? (
            <a className="a-btn is-ghost" href={`${context === "organisation" ? "/org/radar" : "/app/radar"}?scenario=${scenario}`}>{t("range.reset")}</a>
          ) : null}
        </>
      )}

      {directions.ok ? <RoleDirectionsCard signals={directions.data.items} meta={directions.data.meta} organisation={context === "organisation"} snapshotDate={snapshotDate} /> : <ErrorState failure={directions} />}
      <section className="a-card radar-skills-card" aria-labelledby="h-all">
        <div className="a-card-head">
          <h2 id="h-all">{tp("allSkills")}</h2>
        </div>
        <SignalExplorer key={`${scenario}:${meta.snapshot_date}`} items={items} scenario={scenario} />
      </section>
      <MalaysiaContextCard />
    </div>
  );
}
