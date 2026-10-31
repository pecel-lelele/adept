import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const projection = [{ day: "2026-11-25", value: 112.5 }];
const data = {
  kind: "role", start: "2026-08-01", end: "2026-10-26", window_days: 7, step_days: 1,
  available_from: "2026-01-07", available_to: "2026-10-26",
  mode: "indexed", raw_fallback: false, base_date: "2026-08-01", horizon_days: 30,
  projected_from: "2026-10-26", projected_to: "2026-11-25",
  lines: [
    { entity: "role:synthetic-up", kind: "role", entity_id: "synthetic-up", label: "Synthetic rising role",
      start_value: 100, end_value: 110, change: 10, moderate_end: 112.5, fast_end: 118.2,
      points: [{ day: "2026-08-01", value: 100 }, { day: "2026-10-26", value: 110 }], projection },
    { entity: "category:synthetic", kind: "category", entity_id: "synthetic", label: "Synthetic category",
      start_value: 100, end_value: 95, change: -5, moderate_end: 90, fast_end: 80,
      points: [{ day: "2026-08-01", value: null }, { day: "2026-10-26", value: 95 }], projection: [] },
  ],
  options: [
    { entity: "role:synthetic-up", kind: "role", label: "Synthetic rising role" },
    { entity: "role:synthetic-extra", kind: "role", label: "Synthetic extra role" },
    { entity: "category:synthetic-other", kind: "category", label: "Synthetic other category" },
    { entity: "skill:synthetic-skill", kind: "skill", label: "Synthetic skill" },
  ],
  meta: {
    scenario: "fast", is_estimate: true, snapshot_date: "2026-10-26",
    observed_from: "2026-07-26", observed_to: "2026-10-26",
    sources: [{ name: "Synthetic range-paper source", url: "https://example.test/range-papers", retrieved_at: "2026-10-28" }],
  },
  projection_meta: {
    scenario: "fast", is_estimate: true, snapshot_date: "2026-10-26",
    observed_from: "2026-10-13", observed_to: "2026-10-26",
    sources: [{ name: "Synthetic projection baseline", url: "https://example.test/baseline", retrieved_at: "2026-10-20" }],
  },
};
const range = { view: "roles", preset: "3M", entities: ["role:synthetic-up", "category:synthetic"], mode: "indexed", horizon: 30 };

function card(locale: string, charted: unknown[]) {
  const intl = translations(locale);
  const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
  const { TrendRangeCard } = loadComponent("src/features/trends/components/TrendRangeCard.tsx", {
    "@/components": { MetaBar },
    "../range": loadComponent("src/features/trends/range.ts"),
    "next-intl/server": { getTranslations: async (namespace: string) => intl.useTranslations(namespace) },
    "./TrendLinesChart": { TrendLinesChart: (props: unknown) => { charted.push(props); return null; } },
  });
  return TrendRangeCard;
}

const render = async (locale: string, props: object, charted: unknown[] = []) =>
  renderToStaticMarkup(await resolveTree(await card(locale, charted)({ data, range, scenario: "fast", pathname: "/app/radar", ...props })));

test("the card keeps every choice in the URL and blocks dates outside stored data, in every locale", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const charted: { lines: { key: string; entity: string; projection: unknown[] }[] }[] = [];
    const html = await render(locale, { snapshotDate: "2026-10-26" }, charted);
    const t = translations(locale).useTranslations("trends.range");
    assert.match(html, /<form[^>]*action="\/app\/radar#trend"[^>]*method="get"/);
    assert.match(html, /name="scenario" value="fast"/);
    assert.match(html, /name="view" value="roles"/);
    assert.match(html, /name="snapshot_date" value="2026-10-26"/);
    assert.match(html, /name="horizon" value="30"/);
    for (const name of ["from", "to"]) {
      const input = html.match(new RegExp(`<input type="date"[^>]*name="${name}"[^>]*>`))?.[0] ?? "";
      for (const attr of ['min="2026-01-07"', 'max="2026-10-26"']) assert.ok(input.includes(attr), attr);
    }
    const chip = html.match(/<input type="checkbox"[^>]*value="role:synthetic-up"[^>]*>/)?.[0] ?? "";
    assert.ok(chip.includes('name="entity"') && chip.includes('checked=""'), chip);
    // Roles and categories compare together; skills stay on their own tab.
    assert.match(html, /<option value="role:synthetic-extra">Synthetic extra role<\/option>/);
    assert.match(html, /<option value="category:synthetic-other">Synthetic other category<\/option>/);
    assert.doesNotMatch(html, /<option value="skill:synthetic-skill">/);
    assert.doesNotMatch(html, /<option value="role:synthetic-up">/, "shown lines are not offered again");
    for (const view of ["skills", "roles", "categories"]) assert.match(html, new RegExp(`view=${view}`));
    for (const preset of ["1W", "1M", "3M", "6M"]) assert.match(html, new RegExp(`preset=${preset}`));
    assert.match(html, /mode=raw/);
    for (const horizon of [30, 180, 365]) assert.match(html, new RegExp(`horizon=${horizon}`));
    assert.ok(html.includes(t("dataThrough", { date: "2026-10-26" })));
    assert.ok(html.includes(t("derived")));
    assert.deepEqual(charted[0]?.lines.map((l) => [l.key, l.entity]), [["s0", "role:synthetic-up"], ["s1", "category:synthetic"]]);
  }
});

test("observed and projected parts carry separate attribution and the projection is labelled", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const html = await render(locale, {});
    const t = translations(locale).useTranslations("trends.range");
    assert.match(html, /Synthetic range-paper source/);
    assert.match(html, /Synthetic projection baseline/);
    assert.ok(html.includes(t("projectionNote", { scenario: t("scenario.fast"), days: 30 })));
  }
  const en = translations("en").useTranslations("trends.range");
  assert.match(en("projectionNote", { scenario: "fast", days: 30 }), /Pace continuation, not a prediction\./);
  assert.equal(en("projected"), "If this pace continues");
  assert.match(en("derived"), /derived from arXiv skill signals, not observed role demand/);
});

test("the stats table gives start, end, change and both projected endpoints", async () => {
  const html = await render("en", {});
  const row = html.match(/<tr><th scope="row">Synthetic rising role<\/th>(.*?)<\/tr>/)?.[1] ?? "";
  assert.deepEqual([...row.matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1]), ["100.0", "110.0", "+10.0", "112.5", "118.2"]);
});

test("raw mode shows shares and a raw fallback says so", async () => {
  const raw = {
    ...data, mode: "raw", raw_fallback: true, base_date: null,
    lines: [{ ...data.lines[0], start_value: 0.1, end_value: 0.15, change: 0.05, moderate_end: 0.2, fast_end: 0.25 }],
  };
  const html = await render("en", { data: raw });
  const row = html.match(/<tr><th scope="row">Synthetic rising role<\/th>(.*?)<\/tr>/)?.[1] ?? "";
  assert.deepEqual([...row.matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1]), ["10.0%", "15.0%", "+5.0 pp", "20.0%", "25.0%"]);
  assert.match(html, /raw scores are shown instead/);
});

test("the point table keeps gaps under their own dates", async () => {
  const html = await render("en", {});
  const first = html.match(/<tr><th scope="row">2026-08-01<\/th>(.*?)<\/tr>/)?.[1] ?? "";
  assert.deepEqual([...first.matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1]), ["100.0", "–"]);
});

test("an empty store says so instead of drawing an invented chart", async () => {
  const charted: unknown[] = [];
  const html = await render("en", { data: { ...data, lines: [], available_to: null, available_from: null, projection_meta: null }, range: { ...range, view: "skills", entities: [] } }, charted);
  assert.equal(charted.length, 0);
  assert.match(html, /No daily history is stored yet/);
  assert.doesNotMatch(html, /Refresh data/);
});

test("short history explains the incomplete window and keeps the form", async () => {
  const html = await render("en", { data: { ...data, lines: [], available_from: null, available_to: "2026-10-09", projection_meta: null } });
  assert.match(html, /A trend point needs 7 stored days of papers. History is still being collected./);
  assert.match(html, /<form/);
});

test("a rejected choice keeps the form, explains it, and the picker stops at eight lines", async () => {
  const many = Array.from({ length: 8 }, (_, n) => ({ ...data.lines[0], entity: `role:k${n}`, label: `Synthetic role ${n}` }));
  const html = await render("en", { data: { ...data, lines: many }, rejected: true });
  assert.match(html, /role="alert"/);
  assert.match(html, /<form/);
  assert.doesNotMatch(html, /<select/);
  assert.match(html, /Up to 8 lines/);
});

test("chart rows keep gaps, bridge the projection and never interpolate", () => {
  const { chartRows } = loadComponent("src/features/trends/components/TrendLinesChart.tsx", {
    "next-intl": translations("en"),
    recharts: {},
    "@/components/ui/chart": {},
    "../range": loadComponent("src/features/trends/range.ts"),
  });
  const rows = chartRows([
    { key: "s0", label: "a", color: "#000", change: 1,
      points: [{ day: "2026-01-01", value: 1 }, { day: "2026-01-02", value: null }, { day: "2026-01-03", value: 2 }],
      projection: [{ day: "2026-01-10", value: 3 }] },
  ]);
  const plain = (values: unknown) => JSON.parse(JSON.stringify(values));
  assert.deepEqual(plain(rows.map((r: Record<string, unknown>) => r.s0 ?? null)), [1, null, 2, null]);
  assert.deepEqual(plain(rows.map((r: Record<string, unknown>) => r.s0p ?? null)), [null, null, 2, 3]);
});

test("url state parses safely and links keep the other choices", () => {
  const { parseTrendRange, rangeHref } = loadComponent("src/features/trends/range.ts", {});
  const parsed = parseTrendRange({ view: "nope", entity: ["role:a", ""], skill: "python", mode: "x", horizon: "45" });
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), { view: "skills", preset: "3M", entities: ["role:a", "skill:python"], mode: "indexed", horizon: 90 });
  assert.equal(parseTrendRange({ from: "2026-01-01" }).preset, undefined);
  const href = rangeHref("/org/radar", parsed, { scenario: "fast" }, { mode: "raw", horizon: 365 });
  assert.ok(href.startsWith("/org/radar?scenario=fast&view=skills&preset=3M&mode=raw&horizon=365"));
  assert.ok(href.includes("entity=role%3Aa") && href.endsWith("#trend"));
});

test("one contextual trend date replaces duplicate page-level freshness lines", () => {
  const radar = readFileSync("src/web/src/features/trends/components/RadarView.tsx", "utf8");
  const home = readFileSync("src/web/src/features/core/components/DashboardView.tsx", "utf8");
  for (const source of [radar, home]) assert.doesNotMatch(source, /RefreshDataButton|dataThrough/);
  assert.match(radar, /<MetaBar meta=\{meta\}/);
  assert.doesNotMatch(radar, /<DataAsOf/);
  assert.match(home, /<DataAsOf source="trends" meta=\{radar.data.meta\}/);
  assert.match(readFileSync("src/web/src/features/trends/components/DataSourcesPanel.tsx", "utf8"), /RefreshDataButton/);
});

test("quick range stays visible while advanced filters open only for custom choices", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const simple = { ...range, entities: [], horizon: 90 };
    const plain = await render(locale, { range: simple });
    const t = translations(locale).useTranslations("trends.range");
    assert.ok(plain.includes(`<summary class="a-range-editor-summary">${t("adjust")}`));
    assert.match(plain, /<details class="a-range-editor"><summary/);
    assert.ok(plain.indexOf('aria-label="Date range"') < plain.indexOf('class="a-range-editor"') || locale !== "en");
    assert.ok(plain.includes(t("title")) && plain.includes(t("dataThrough", { date: data.available_to })));
    for (const changed of [
      { ...simple, from: "2026-08-01", preset: undefined },
      { ...simple, entities: ["role:synthetic-up"] },
      { ...simple, mode: "raw" },
      { ...simple, horizon: 180 },
    ]) {
      const html = await render(locale, { range: changed });
      assert.match(html, /<details class="a-range-editor" open=""><summary/);
    }
    const rejected = await render(locale, { range: simple, rejected: true });
    assert.match(rejected, /<details class="a-range-editor" open=""><summary/);
  }
});
