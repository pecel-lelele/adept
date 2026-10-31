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
  meta: { scenario: "fast" },
};

function card(locale: string, charted: unknown[]) {
  const intl = translations(locale);
  const { TrendRangeCard } = loadComponent("src/features/trends/components/TrendRangeCard.tsx", {
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
