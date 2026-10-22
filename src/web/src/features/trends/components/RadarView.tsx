import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import { Scene3D, TrendBars } from "@/components/viz";
import type { ScenarioId } from "@/lib/api";

import { fetchRadar } from "../api";
import { SignalExplorer } from "./SignalExplorer";

/**
 * Step 2, the Future Skills Radar. Hierarchy: how many skills rise / hold / decline →
 * the strongest movers as a diverging chart → the full searchable list, collapsed.
 */
export async function RadarView({
  scenario,
  snapshotDate,
  context = "individual",
}: {
  scenario: ScenarioId;
  snapshotDate?: string;
  context?: "individual" | "organisation";
}) {
  const t = await getTranslations("trends");
  const d = await getTranslations("common.design");
  const result = await fetchRadar(scenario, snapshotDate);
  if (!result.ok) return <ErrorState failure={result} />;
  const { items, meta } = result.data;
  const v = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const dir = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const count = (x: string) => items.filter((i) => i[dir] === x).length;
  const sorted = [...items].sort((a, b) => b[v] - a[v]);
  const movers = [...sorted.slice(0, 7), ...sorted.slice(-7).filter((i) => i[v] < 0)]
    .filter((i, n, all) => all.findIndex((x) => x.skill_id === i.skill_id) === n)
    .map((i) => ({ id: i.skill_id, label: i.skill_label, value: i[v], direction: i[dir] }));

  return (
    <div className="a-stack">
      <section className="a-hero" style={{ minHeight: 0 }}>
        <div>
          <span className="a-eyebrow">
            {meta.snapshot_date} · {meta.sources.map((s) => s.name).join(" + ")}
          </span>
          <h1>{context === "organisation" ? t("orgTitle") : t("title")}</h1>
          <div className="a-stats" style={{ maxWidth: 460 }}>
            <div className="a-stat" style={{ background: "#e3f3e9" }}>
              <strong style={{ color: "var(--a-up)" }}>▲ {count("rising")}</strong>
              <span>{d("rising")}</span>
            </div>
            <div className="a-stat">
              <strong>• {count("stable")}</strong>
              <span>{d("stable")}</span>
            </div>
            <div className="a-stat" style={{ background: "#f9e6e1" }}>
              <strong style={{ color: "var(--a-down)" }}>▼ {count("declining")}</strong>
              <span>{d("declining")}</span>
            </div>
          </div>
        </div>
        <Scene3D variant="orbit" />
      </section>

      <section className="a-card">
        <div className="a-card-head">
          <h2>{d("skills")}</h2>
          <span className="a-chip">{d("rising")} / {d("declining")}</span>
        </div>
        <TrendBars items={movers} />
      </section>

      <details className="a-card">
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>
          {d("explore")} · {items.length}
        </summary>
        <div style={{ marginTop: 16 }}>
          <SignalExplorer items={items} scenario={scenario} dates={meta.available_snapshots} date={meta.snapshot_date} />
        </div>
      </details>
      <MetaBar meta={meta} />
      {meta.data_provenance_note ? <p className="a-small a-muted">{meta.data_provenance_note}</p> : null}
    </div>
  );
}
