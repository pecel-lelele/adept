import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const view = readFileSync("src/web/src/features/impact/components/ImpactView.tsx", "utf8");
const evidence: Array<Record<string, unknown>> = JSON.parse(
  readFileSync("src/data/seed/impact/public_evidence.json", "utf8"),
);

test("the page renders every public evidence field from the API response", () => {
  for (const field of ["public_evidence", "item.figure", "item.quote", "item.publisher", "item.url", "item.retrieved_at"]) {
    assert.ok(view.includes(field), `ImpactView must render ${field}`);
  }
  assert.ok(view.includes("fetchImpact"), "data must come from the impact API");
});

test("no evidence figure or quote is hard-coded in components or messages", () => {
  const texts = [view];
  for (const locale of ["en", "ms", "zh"]) {
    texts.push(readFileSync(`src/web/messages/${locale}/impact.json`, "utf8"));
  }
  for (const item of evidence) {
    for (const key of ["figure", "quote"] as const) {
      for (const text of texts) assert.ok(!text.includes(String(item[key])), `${item.id}.${key} is hard-coded`);
    }
  }
});

test("every stored evidence item has a source, a date and a short quote", () => {
  assert.ok(evidence.length >= 4 && evidence.length <= 6);
  for (const item of evidence) {
    assert.match(String(item.url), /^https:\/\//);
    assert.ok(String(item.publisher).length > 0);
    assert.match(String(item.retrieved_at), /^\d{4}-\d{2}-\d{2}$/);
    const quote = String(item.quote).trim();
    assert.ok(quote.length > 0 && quote.split(/\s+/).length <= 15);
  }
});

test("the honest line and impact namespace exist in every locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const messages = JSON.parse(readFileSync(`src/web/messages/${locale}/impact.json`, "utf8"));
    assert.ok(messages.honest && messages.basis.includes("{count}"));
  }
  assert.ok(readdirSync("src/web/messages/en").includes("impact.json"));
});

test("coverage, sourced public evidence and archived-sample context render in every locale", async () => {
  const aggregate = { median_free_course_share: .5, median_free_hours_share: .4, median_hrd_course_share: 0,
    median_total_hours: 8, median_sdg_target_count: 2, median_top5_changed: 0 };
  const data = {
    personas: [], aggregates: [ { scenario: "moderate", ...aggregate }, { scenario: "fast", ...aggregate } ],
    meta: { snapshot_date: "2026-10-20", observed_from: "2024-10-13", observed_to: "2024-10-19", sources: [{ retrieved_at: "2026-10-20" }] },
    catalogue: { course_count: 3, role_count: 2, target_role_count: 1, skill_count: 5, free_course_share: 2/3,
      free_course_count: 2, free_hours: 10, sdg_target_count: 2, role_sdg_link_count: 3, by_language: [{ key: "en", count: 3 }],
      by_provider_type: [], verified_recent_share: 1, verified_window_days: 30, as_of: "2026-10-30" },
    fairness: { max_rank_change: 0, variants_tested: 15, guardrail_report_passed: true },
    public_evidence: [{ id: "synthetic-test-evidence", figure: "42", scope: "Synthetic fixture", claim: "Synthetic context only",
      quote: "Synthetic quote", publisher: "Fixture publisher", url: "https://example.test/evidence",
      retrieved_at: "2026-10-30", published_at: "2025-01-07", feature: "pathway" }],
  };
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { ImpactView } = loadComponent("src/features/impact/components/ImpactView.tsx", {
      "next-intl/server": { getTranslations: async (namespace) => intl.useTranslations(namespace) },
      "@/components": { MetaBar: () => null, ErrorState: () => React.createElement("p", {}, "Unexpected error") },
      "@/components/shell/Site": { SiteHeader: () => null, SiteFooter: () => null },
      "../api": { fetchImpact: async () => ({ ok: true, data }) },
      "./impact.module.css": { default: {} },
    });
    const html = renderToStaticMarkup(await resolveTree(await ImpactView({})));
    const t = intl.useTranslations("impact");
    assert.ok(html.includes(t("catalogueFree.note", { count: "2", hours: "10" })));
    assert.ok(html.includes(t("catalogueSdg.note", { links: "3", targets: "1" })));
    assert.ok(html.includes(t("basisArchived", { count: "0" })));
    assert.doesNotMatch(html, /Historical replay|Details & sources/);
    assert.ok(html.includes(t("published", { date: "2025-01-07" })));
    assert.ok(html.includes("Synthetic context only") && html.includes("Fixture publisher"));
    assert.doesNotMatch(html, /RM|Unexpected error|total_cost/);
  }
});
