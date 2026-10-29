import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

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
    assert.match(html, /12.0/);
    assert.ok(html.includes(translations(locale).useTranslations("matching")("noClosingCourse")));
  }
});

test("scenario delta uses API score differences and never invents an unavailable comparison", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { ScenarioDelta } = loadComponent("src/features/matching/components/ScenarioDelta.tsx", {
      "next-intl": translations(locale),
    });
    const html = renderToStaticMarkup(React.createElement(ScenarioDelta, {
      score: 0.72, otherScore: 0.695, otherScenario: "moderate",
    }));
    assert.match(html, /\+2.5/);
    assert.match(html, /data-tone="up"/);
    assert.equal(renderToStaticMarkup(React.createElement(ScenarioDelta, {
      score: 0.72, otherScenario: "fast",
    })), "");
  }
});
