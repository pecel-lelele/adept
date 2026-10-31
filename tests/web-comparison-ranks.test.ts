import assert from "node:assert/strict";
import test from "node:test";
import * as navigation from "../src/web/src/config/navigation.ts";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

test("small-cohort cells and row summaries stay neutral and never become zero-gap data", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const label = intl.useTranslations("ui.org")("tooFewMembers");
    const { Heatmap } = loadComponent("src/components/viz/Heatmap.tsx");
    const nothing = () => null;
    const { topGapSkills, heatRows } = loadComponent("src/features/org/components/OrgDashboardView.tsx", {
      "@/features/trends/components/MalaysiaContextCard": { MalaysiaContextCard: nothing },
      "@/features/trends/components/AdminTrendRefresh": { AdminTrendRefresh: nothing },
      "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
      "@/components": {}, "@/components/ErrorState": {}, "@/components/viz": {},
      "@/features/sdg/api": {}, "@/features/sdg/components/SdgLinkCards": {}, "../programmes/api": {}, "../api": {}, "./JoinCodeCard": {},
    });
    const data = { role_ids: ["synthetic-role"], skills: [{ id: "synthetic-skill", label: "Synthetic skill" }], cells: [{ role_id: "synthetic-role", skill_id: "synthetic-skill", gap: null, suppressed: true }], role_gaps: { "synthetic-role": null }, role_suppressed: { "synthetic-role": true }, meta: {} };
    const skills = topGapSkills(data, 14);
    assert.equal(skills.length, 1);
    const rows = heatRows(data, skills);
    assert.equal(rows[0].cells[0].value, null);
    const html = renderToStaticMarkup(React.createElement(Heatmap, { rows, columns: skills, legend: ["low", "high"], suppressedLabel: label }));
    assert.ok(html.includes(label));
    assert.match(html, /background:var\(--a-heat-suppressed\)/);
    assert.match(html, /<p[^>]*role="note"[^>]*>[^<]+<\/p>/);
    assert.doesNotMatch(html, /#eef1e7|>0<|>0%/);
    const { GapsView } = loadComponent("src/features/org/components/GapsView.tsx", {
      "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) },
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
      "@/components": { Kpis: nothing, MetaBar: nothing, PageHeader: nothing }, "@/config/navigation": navigation,
      "@/components/ErrorState": {}, "@/components/viz": { Heatmap },
      "../api": { fetchGaps: async () => ({ ok: true, data }) }, "./OrgDashboardView": { heatRows, topGapSkills },
    });
    const page = renderToStaticMarkup(await resolveTree(await GapsView({ scenario: "moderate" })));
    assert.ok(page.includes(label));
    assert.doesNotMatch(page, /a-scorebar|>0%/);
  }
});
