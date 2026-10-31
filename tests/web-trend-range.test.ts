import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

const series = {
  start: "2026-10-12", end: "2026-10-26", window_days: 7,
  available_from: "2026-10-12", available_to: "2026-10-26",
  lines: [
    { skill_id: "python", label: "Synthetic rising skill", change: 0.05,
      points: [{ day: "2026-10-12", share: 0.1 }, { day: "2026-10-26", share: 0.15 }] },
    { skill_id: "sql", label: "Synthetic falling skill", change: -0.02,
      points: [{ day: "2026-10-12", share: null }, { day: "2026-10-26", share: 0.08 }] },
  ],
  meta: {
    scenario: "fast", is_estimate: false, snapshot_date: "2026-10-26",
    observed_from: "2026-10-06", observed_to: "2026-10-26",
    sources: [{ name: "Synthetic range-paper source", url: "https://example.test/range-papers", retrieved_at: "2026-10-28" }],
  },
};

function card(locale: string, charted: unknown[]) {
  const intl = translations(locale);
  const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
  const { TrendRangeCard } = loadComponent("src/features/trends/components/TrendRangeCard.tsx", {
    "@/components": { MetaBar },
    "next-intl/server": { getTranslations: async (namespace: string) => intl.useTranslations(namespace) },
    "./TrendLinesChart": { TrendLinesChart: (props: unknown) => { charted.push(props); return null; } },
  });
  return TrendRangeCard;
}

test("trend range keeps scenario and date limits in a plain GET form in every locale", async () => {
  for (const locale of ["en", "ms", "zh"]) {
    const charted: { lines: { key: string; skillId: string; points: unknown[] }[] }[] = [];
    const TrendRangeCard = card(locale, charted);
    const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
      series, scenario: "fast", snapshotDate: "2026-10-26", pathname: "/app/radar",
      allSkills: [{ id: "python", label: "Synthetic rising skill" }, { id: "rust", label: "Synthetic extra skill" }],
    })));
    assert.match(html, /<form[^>]*action="\/app\/radar"[^>]*method="get"/);
    assert.match(html, /Synthetic range-paper source/);
    assert.match(html, /href="https:\/\/example.test\/range-papers"/);
    assert.ok(html.includes(translations(locale).useTranslations("common.design")("observed", {
      from: series.meta.observed_from, to: series.meta.observed_to,
    })));
    assert.match(html, /name="scenario" value="fast"/);
    assert.match(html, /name="snapshot_date" value="2026-10-26"/);
    const from = html.match(/<input type="date"[^>]*name="from"[^>]*>/)?.[0] ?? "";
    for (const attr of ['min="2026-10-12"', 'max="2026-10-26"', 'value="2026-10-12"']) assert.ok(from.includes(attr), attr);
    const chip = html.match(/<input type="checkbox"[^>]*value="python"[^>]*>/)?.[0] ?? "";
    assert.ok(chip.includes('name="skill"') && chip.includes('checked=""'), chip);
    assert.match(html, /<option value="rust">Synthetic extra skill<\/option>/);
    assert.doesNotMatch(html, /<option value="python">/, "shown skills are not offered again");
    assert.match(html, /\+5\.0 pp/);
    assert.match(html, /-2\.0 pp/);
    const lines = charted[0]?.lines ?? [];
    assert.deepEqual(lines.map((l) => [l.key, l.skillId]), [["s0", "python"], ["s1", "sql"]]);
  }
});

test("an empty store says so instead of drawing an invented chart", async () => {
  const charted: unknown[] = [];
  const TrendRangeCard = card("en", charted);
  const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
    series: { ...series, lines: [], available_to: null, available_from: null },
    scenario: "moderate", pathname: "/org/radar", allSkills: [],
  })));
  assert.equal(charted.length, 0);
  assert.match(html, /No daily history is stored yet/);
});

test("short history explains the incomplete window and keeps the form", async () => {
  const TrendRangeCard = card("en", []);
  const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
    series: { ...series, lines: [], available_from: null, available_to: "2026-10-09" },
    scenario: "fast", pathname: "/app/radar", allSkills: [],
  })));
  assert.match(html, /A trend point needs 7 stored days of papers. History is still being collected./);
  assert.doesNotMatch(html, /No skill moved in this range/);
  assert.match(html, /<form[^>]*action="\/app\/radar"[^>]*method="get"/);
});

test("the table lists every day with gaps under their own dates", async () => {
  const TrendRangeCard = card("en", []);
  const uneven = {
    ...series,
    lines: [
      { skill_id: "python", label: "Synthetic rising skill", change: 0.05,
        points: [{ day: "2026-10-12", share: 0.1 }, { day: "2026-10-26", share: 0.15 }] },
      { skill_id: "sql", label: "Synthetic uneven skill", change: -0.02,
        points: [{ day: "2026-10-26", share: 0.08 }] },
    ],
  };
  const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
    series: uneven, scenario: "fast", pathname: "/app/radar", allSkills: [],
  })));
  const first = html.match(/<tr><th scope="row">2026-10-12<\/th>(.*?)<\/tr>/)?.[1] ?? "";
  assert.deepEqual([...first.matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1]), ["10.0%", "–"]);
  const last = html.match(/<tr><th scope="row">2026-10-26<\/th>(.*?)<\/tr>/)?.[1] ?? "";
  assert.deepEqual([...last.matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1]), ["15.0%", "8.0%"]);
});

test("short history date inputs do not render an unusable minimum", async () => {
  for (const availableTo of [null, "2026-10-09"] as const) {
    const TrendRangeCard = card("en", []);
    const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
      series: { ...series, start: "2026-10-06", end: "2026-10-09", available_from: null, available_to: availableTo },
      scenario: "fast", pathname: "/app/radar", allSkills: [],
    })));
    const inputs = [...html.matchAll(/<input type="date"[^>]*>/g)].map((m) => m[0]);
    assert.equal(inputs.length, 2);
    for (const input of inputs) {
      assert.doesNotMatch(input, /\smin=""/);
      assert.doesNotMatch(input, /\smin="/);
      const min = input.match(/\smin="([^"]+)"/)?.[1];
      const max = input.match(/\smax="([^"]+)"/)?.[1];
      if (min && max) assert.ok(min <= max, input);
    }
  }
});

test("a rejected choice keeps the form, explains it, and the picker stops at eight skills", async () => {
  const TrendRangeCard = card("en", []);
  const many = Array.from({ length: 8 }, (_, n) => ({ ...series.lines[0], skill_id: `k${n}`, label: `Synthetic skill ${n}` }));
  const html = renderToStaticMarkup(await resolveTree(await TrendRangeCard({
    series: { ...series, lines: many }, scenario: "fast", pathname: "/app/radar", rejected: true,
    allSkills: [{ id: "rust", label: "Synthetic extra skill" }],
  })));
  assert.match(html, /role="alert"/);
  assert.match(html, /<form/);
  assert.match(html, /href="\/app\/radar\?scenario=fast"/);
  assert.doesNotMatch(html, /<select/);
  assert.match(html, /Up to 8 skills/);
});
