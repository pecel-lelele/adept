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
