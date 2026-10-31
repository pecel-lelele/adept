import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

test("zero-skill matches show the translated add-skills notice in list and detail views", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { ProfileNote } = loadComponent("src/features/matching/components/ProfileNote.tsx", { "next-intl": translations(locale) });
    const html = renderToStaticMarkup(React.createElement(ProfileNote, { note: "add_skills" }));
    assert.ok(html.includes(translations(locale).useTranslations("matching")("addSkillsNote")));
    assert.match(html, /role="status"/);
    assert.equal(renderToStaticMarkup(React.createElement(ProfileNote, {})), "");
  }
});

test("match cards show only the top three improvements with grounded course links or an honest gap", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { MatchImprovements } = loadComponent("src/features/matching/components/MatchImprovements.tsx", {
      "next-intl": translations(locale),
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
    });
    const items = [0.12, 0.09, 0.03, 0.01].map((gain, index) => ({
      skill: `synthetic-${index}`, label: `Synthetic skill ${index}`, score_gain: gain,
      course_id: index ? null : "synthetic-course", course_title: index ? null : "Synthetic course",
      course_url: index ? null : "https://example.test/course",
    }));
    const html = renderToStaticMarkup(React.createElement(MatchImprovements, { items }));
    assert.equal((html.match(/<li>/g) ?? []).length, 3);
    assert.match(html, /href="https:\/\/example.test\/course"/);
    assert.doesNotMatch(html, /Synthetic skill 3/);
    assert.ok(html.includes(translations(locale).useTranslations("matching")("noClosingCourse")));
  }
});

test("every SDG tile on a match card has its mapping reason as a tooltip and as visible text", () => {
  const { SdgTiles } = loadComponent("src/components/viz/SdgTiles.tsx");
  const { MatchSdgTargets } = loadComponent("src/features/matching/components/MatchSdgTargets.tsx", {
    "next-intl": translations(), "@/components/viz": { SdgTiles },
  });
  const targets = [
    { goal: 4, target: "4.4", label: "Synthetic target label", reason: "Synthetic reason one", strength: "direct" },
    { goal: 4, target: "4.3", label: "Synthetic target label two", reason: "Synthetic reason two", strength: "enabling" },
    { goal: 8, target: "8.2", label: "Synthetic target label three", reason: "Synthetic reason three", strength: "enabling" },
  ];
  const html = renderToStaticMarkup(React.createElement(MatchSdgTargets, { targets }));
  const chips = html.match(/<li[^>]*data-sdg-reason[^>]*>/g) ?? [];
  assert.equal(chips.length, 2);
  for (const chip of chips) assert.match(chip, /data-sdg-reason="[^"]+"/);
  // Reasons are also visible text in a keyboard/touch-operable disclosure, not only a title.
  const why = html.match(/<details[^>]*>[\s\S]*<\/details>/)?.[0] ?? "";
  assert.match(why, /<summary/);
  for (const target of targets) {
    assert.ok(why.includes(`>${target.reason}<`) || why.includes(` · ${target.reason}`), target.reason);
    assert.ok(why.includes(target.target));
  }
  assert.match(html, /direct/);
  assert.match(html, /enabling/);
});

