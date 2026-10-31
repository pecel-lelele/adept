import assert from "node:assert/strict";
import test from "node:test";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const meta = {
  snapshot_date: "2026-10-20", scenario: "moderate", is_estimate: true,
  served_from: "fixture", is_fallback: true,
  sources: [{ name: "Synthetic source", url: "https://example.test", retrieved_at: "2026-10-19" }],
};

test("attribution is one small Sources link whose accessible name keeps the estimate and fallback cues", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { MetaBar } = loadComponent("src/components/MetaBar.tsx", {
      "next-intl": intl, "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
    });
    const html = renderToStaticMarkup(React.createElement(MetaBar, { meta }));
    assert.match(html, /href="\/about#data-sources"/);
    assert.doesNotMatch(html, /<details|<summary|Moderate AI change|Fast AI change/);
    const label = html.match(/aria-label="([^"]*)"/)![1];
    assert.ok(label.includes(intl.useTranslations("common.estimate")("hint")));
    assert.ok(label.includes("2026-10-20"));
    assert.ok(label.includes(intl.useTranslations("common.freshness")("fallbackShort")));
    assert.ok(html.includes(intl.useTranslations("common.design")("sources")));
  }
});

test("the estimate label is announced to screen readers and never drawn as a chip", () => {
  const intl = translations("en");
  const { EstimateLabel } = loadComponent("src/components/EstimateLabel.tsx", { "next-intl": intl });
  const html = renderToStaticMarkup(React.createElement(EstimateLabel, { isEstimate: true }));
  assert.match(html, /class="a-sr"/);
  assert.ok(html.includes("Estimate"));
  assert.equal(renderToStaticMarkup(React.createElement(EstimateLabel, { isEstimate: false })), "");
});

test("sources are a flat line with names and retrieval dates, not an expander", () => {
  const intl = translations("en");
  const { SourceBadge } = loadComponent("src/components/SourceBadge.tsx", { "next-intl": intl });
  const html = renderToStaticMarkup(React.createElement(SourceBadge, { sources: meta.sources }));
  assert.doesNotMatch(html, /<details|<summary/);
  assert.match(html, /Synthetic source/);
  assert.match(html, /2026-10-19/);
});
