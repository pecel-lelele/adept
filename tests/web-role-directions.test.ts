import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

test("radar groups public role signals and keeps dated exploration explicit", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { RoleDirectionsCard } = loadComponent("src/features/trends/components/RoleDirectionsCard.tsx", {
      "next-intl": translations(locale), "@/components/MetaBar": { MetaBar: () => null },
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
    });
    const props = {
      signals: [
        { entity_type: "role", entity_id: "synthetic-up", label: "Synthetic rising role", direction: "rising", growth_rate: 0.2 },
        { entity_type: "role", entity_id: "synthetic-down", label: "Synthetic declining role", direction: "declining", growth_rate: -0.2 },
        { entity_type: "role", entity_id: "synthetic-stable", label: "Synthetic stable role", direction: "stable", growth_rate: 0 },
        { entity_type: "skill", entity_id: "synthetic-skill", label: "Synthetic skill", direction: "rising", growth_rate: 0.3 },
      ], meta: { scenario: "fast", snapshot_date: "2026-10-20", sources: [], is_estimate: true },
    };
    const html = renderToStaticMarkup(React.createElement(RoleDirectionsCard, props));
    assert.match(html, /Synthetic rising role/);
    assert.match(html, /Synthetic declining role/);
    assert.doesNotMatch(html, /Synthetic stable role/);
    assert.doesNotMatch(html, /Synthetic skill/);
    assert.match(html, /data-direction="rising"/);
    assert.match(html, /data-direction="declining"/);
    assert.doesNotMatch(html, /snapshot_date/);
    const dated = renderToStaticMarkup(React.createElement(RoleDirectionsCard, { ...props, snapshotDate: "2026-10-13" }));
    assert.match(dated, /snapshot_date=2026-10-13/);
  }
});

test("organisation radar renders role directions without loading personal intake or plans", async () => {
  const intl = translations();
  const calls: unknown[] = [];
  const meta = { snapshot_date: "2026-10-13", scenario: "fast", sources: [], is_estimate: true, available_snapshots: ["2026-10-13"] };
  const { RadarView } = loadComponent("src/features/trends/components/RadarView.tsx", {
    "./radar.css": {},
    "./MalaysiaContextCard": { MalaysiaContextCard: () => null },
    "@/components/DataAsOf": { DataAsOf: () => null },
    "@/components/SnapshotPicker": { SnapshotPicker: () => null },
    "@/lib/auth/account": { getAccount: async () => null },
    "next-intl": intl,
    "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
    "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
    "@/components": { Kpis: () => null, MetaBar: () => null, PageHeader: () => null, TrendPill: () => null },
    "@/components/MetaBar": { MetaBar: () => null },
    "@/config/navigation": { journeyStepCount: () => 5 },
    "@/components/ErrorState": { ErrorState: () => React.createElement("p", {}, "Unexpected failure") },
    "@/components/viz": { TrendBars: () => null },
    "@/features/profile/api": { fetchMyProfile: () => { throw new Error("No personal intake"); } },
    "@/features/pathway/api": { fetchCompare: () => { throw new Error("No personal learning plan"); } },
    "./SignalExplorer": { SignalExplorer: () => null },
    "./TrendRangeCard": { TrendRangeCard: () => null },
    "../range": loadComponent("src/features/trends/range.ts"),
    "../api": {
      fetchRadar: async () => ({ ok: true, data: { items: [], meta } }),
      fetchCompare: async () => ({ ok: true, data: { lines: [] } }),
      fetchRoleDirections: async (...args) => {
        calls.push(args);
        return { ok: true, data: { meta, items: [
          { entity_type: "role", entity_id: "synthetic-up", label: "Synthetic rising role", direction: "rising", growth_rate: 0.2 },
          { entity_type: "role", entity_id: "synthetic-down", label: "Synthetic declining role", direction: "declining", growth_rate: -0.2 },
        ] } };
      },
    },
  });
  const html = renderToStaticMarkup(await RadarView({ scenario: "fast", context: "organisation" }));
  assert.deepEqual(calls, [["fast", "2026-10-13"]]);
  assert.match(html, /Synthetic rising role/);
  assert.match(html, /Synthetic declining role/);
  assert.match(html, /\/org\/plan\?role=synthetic-up&amp;scenario=fast/);
  assert.doesNotMatch(html, /Unexpected failure/);
});

test("long role lists start at 5 and low coverage stays outside directional claims", () => {
  const { RoleDirectionsCard } = loadComponent("src/features/trends/components/RoleDirectionsCard.tsx", {
    "next-intl": translations(), "@/components/MetaBar": { MetaBar: () => null },
    "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
  });
  const signals = Array.from({ length: 13 }, (_, i) => ({
    entity_type: "role", entity_id: `synthetic-role-${i}`, label: `Synthetic role ${i}`,
    direction: "declining", growth_rate: i / 100 - 1, trend_coverage: 0.75,
  }));
  signals.push({ entity_type: "role", entity_id: "synthetic-thin", label: "Synthetic thin evidence",
    direction: "declining", growth_rate: -2, trend_coverage: 0.25 });
  const html = renderToStaticMarkup(React.createElement(RoleDirectionsCard, {
    signals, meta: { scenario: "moderate", snapshot_date: "2026-10-20", sources: [] },
  }));
  const directional = html.slice(html.indexOf('data-direction="declining"'), html.indexOf('data-direction="insufficient"'));
  const initialRows = directional.slice(0, directional.indexOf('class="radar-role-reveal"'));
  assert.equal((initialRows.match(/class="radar-role-row"/g) ?? []).length, 5);
  assert.match(directional, /View all 13/);
  assert.match(directional, /aria-expanded="false"/);
  assert.match(directional, /radar-role-preview/);
  assert.match(directional, /aria-hidden="true" inert=""/);
  assert.match(directional, /trend data for 75%/);
  assert.doesNotMatch(directional, /Synthetic thin evidence/);
  assert.match(html.slice(html.indexOf('data-direction="insufficient"')), /Synthetic thin evidence/);
});

test("published snapshot selection updates radar counts, roles and evidence while chart dates stay separate", async () => {
  const intl = translations("en");
  const reads: { radar: string[]; roles: string[]; chart: string[] } = { radar: [], roles: [], chart: [] };
  const dates = ["2026-10-13", "2026-10-20"];
  const { RadarView } = loadComponent("src/features/trends/components/RadarView.tsx", {
    "./radar.css": {}, "./MalaysiaContextCard": { MalaysiaContextCard: () => null },
    "next-intl/server": { getTranslations: async (namespace: string) => intl.useTranslations(namespace) },
    "@/components": {
      PageHeader: ({ title, actions, children }) => React.createElement("header", {}, title, actions, children),
      MetaBar: ({ meta }) => React.createElement("p", { "data-snapshot": meta.snapshot_date }, meta.snapshot_date),
      Kpis: ({ items }) => React.createElement("p", { "data-counts": true }, items.map((item) => `${item.label}: ${item.value}`).join(" / ")),
      EstimateLabel: () => null,
      TrendPill: () => null,
    },
    "@/components/SnapshotPicker": { SnapshotPicker: ({ value }) => React.createElement("select", { "data-selection": value }) },
    "@/components/ErrorState": { ErrorState: () => null },
    "@/components/viz": { TrendBars: () => null },
    "@/config/navigation": { journeyStepCount: () => 6 },
    "@/features/profile/api": { fetchMyProfile: () => { throw new Error("organisation has no personal data"); } },
    "./SignalExplorer": { SignalExplorer: ({ items }) => React.createElement("p", {}, items[0]?.skill_label) },
    "./RoleDirectionsCard": { RoleDirectionsCard: ({ meta }) => React.createElement("p", { "data-role-date": true }, meta.snapshot_date) },
    "./TrendRangeCard": { TrendRangeCard: () => null },
    "../range": loadComponent("src/features/trends/range.ts"),
    "../api": {
      fetchRadar: async (_scenario: string, selected: string) => {
        reads.radar.push(selected);
        const date = selected || dates[1];
        const direction = date === dates[0] ? "rising" : "declining";
        return { ok: true, data: { items: [{ skill_id: "synthetic-skill", skill_label: `Synthetic ${direction} skill`,
          velocity_moderate: direction === "rising" ? 0.2 : -0.2, velocity_fast: 0.3,
          direction_moderate: direction, direction_fast: direction, automation_exposure: 0.3 }],
          meta: { snapshot_date: date, available_snapshots: dates, scenario: "moderate", sources: [] } } };
      },
      fetchRoleDirections: async (_scenario: string, date: string) => {
        reads.roles.push(date);
        return { ok: true, data: { items: [], meta: { snapshot_date: date } } };
      },
      fetchCompare: async ({ end }: { end: string }) => {
        reads.chart.push(end);
        return { ok: false, status: 503, code: "storage_unavailable" };
      },
    },
  });
  const range = { view: "skills", entities: [], from: "2026-10-01", to: "2026-10-10", mode: "raw", horizon: 90 };
  const early = renderToStaticMarkup(await resolveTree(await RadarView({ scenario: "moderate", context: "organisation", snapshotDate: dates[0], range })));
  const late = renderToStaticMarkup(await resolveTree(await RadarView({ scenario: "moderate", context: "organisation", snapshotDate: dates[1], range })));
  assert.match(early, /Rising: 1/);
  assert.match(late, /Declining: 1/);
  assert.match(early, /data-role-date="true">2026-10-13/);
  assert.match(late, /data-role-date="true">2026-10-20/);
  assert.match(early, /data-selection="2026-10-13"/);
  assert.deepEqual(reads, { radar: dates, roles: dates, chart: ["2026-10-10", "2026-10-10"] });
});
