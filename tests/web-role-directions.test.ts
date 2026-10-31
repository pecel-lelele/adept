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
      ], meta: { scenario: "fast" },
    };
    const html = renderToStaticMarkup(React.createElement(RoleDirectionsCard, props));
    assert.match(html, /Synthetic rising role/);
    assert.match(html, /Synthetic declining role/);
    assert.doesNotMatch(html, /Synthetic stable role/);
    assert.doesNotMatch(html, /Synthetic skill/);
    assert.match(html, /data-dir="rising"/);
    assert.match(html, /data-dir="declining"/);
    assert.doesNotMatch(html, /snapshot_date/);
    const dated = renderToStaticMarkup(React.createElement(RoleDirectionsCard, { ...props, snapshotDate: "2026-10-13" }));
    assert.match(dated, /snapshot_date=2026-10-13/);
  }
});

test("organisation radar renders role directions without loading personal intake or plans", async () => {
  const intl = translations();
  const calls: unknown[] = [];
  const meta = { snapshot_date: "2026-10-13", scenario: "fast", available_snapshots: ["2026-10-13"] };
  const { RadarView } = loadComponent("src/features/trends/components/RadarView.tsx", {
    "@/components/DataAsOf": { DataAsOf: () => null },
    "@/lib/auth/account": { getAccount: async () => null },
    "./RefreshDataButton": { RefreshDataButton: () => null },
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
    "../api": {
      fetchRadar: async () => ({ ok: true, data: { items: [], meta } }),
      fetchSeries: async () => ({ ok: true, data: { lines: [] } }),
      fetchRoleDirections: async (...args) => {
        calls.push(args);
        return { ok: true, data: { meta, items: [
          { entity_type: "role", entity_id: "synthetic-up", label: "Synthetic rising role", direction: "rising", growth_rate: 0.2 },
          { entity_type: "role", entity_id: "synthetic-down", label: "Synthetic declining role", direction: "declining", growth_rate: -0.2 },
        ] } };
      },
    },
  });
  const html = renderToStaticMarkup(await resolveTree(await RadarView({ scenario: "fast", context: "organisation" })));
  assert.deepEqual(calls, [["fast", "2026-10-13"]]);
  assert.match(html, /Synthetic rising role/);
  assert.match(html, /Synthetic declining role/);
  assert.match(html, /\/org\/plan\?role=synthetic-up&amp;scenario=fast/);
  assert.doesNotMatch(html, /Unexpected failure/);
});
