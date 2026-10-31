import assert from "node:assert/strict";
import test from "node:test";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const meta = {
  snapshot_date: "2026-10-20", scenario: "moderate", is_estimate: true,
  served_from: "fixture", is_fallback: true,
  sources: [{ name: "Synthetic source", url: "https://example.test", retrieved_at: "2026-10-19" }],
};

test("fallback remains visible in the compact citation summary in every locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
    const html = renderToStaticMarkup(React.createElement(MetaBar, { meta }));
    const summary = html.match(/<summary>([\s\S]*?)<\/summary>/)![1];
    assert.match(summary, /role="status"/);
    assert.ok(summary.includes(intl.useTranslations("common.freshness")("fallbackShort")));
    assert.ok(summary.includes("2026-10-20") && summary.includes("Synthetic source"));
    assert.doesNotMatch(html.split("<details")[0], /a-notice/);
    const live = renderToStaticMarkup(React.createElement(MetaBar, { meta: { ...meta, is_fallback: false } }));
    assert.doesNotMatch(live.match(/<summary>([\s\S]*?)<\/summary>/)![1], /role="status"/);
  }
});

test("historical estimates stay labelled while real observation and retrieval dates move into details", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const intl = translations(locale);
    const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
    for (const served_from of ["db", "fixture"]) {
      const html = renderToStaticMarkup(React.createElement(MetaBar, { meta: {
        ...meta, served_from, is_fallback: served_from === "fixture", is_replay: true,
        observation_window_start: "2024-10-13", observation_window_end: "2024-10-19",
        retrieved_at: "2026-10-24", retrieved_at_basis: "git_commit_date",
        data_provenance_note: "Synthetic frozen export provenance",
      } }));
      const summary = html.match(/<summary>([\s\S]*?)<\/summary>/)![1];
      assert.ok(summary.includes(intl.useTranslations("common.estimate")("historical")));
      assert.doesNotMatch(summary, /2024-10|fetch time|Synthetic frozen export/);
      const details = html.split('class="a-metabar-body"')[1];
      for (const value of ["2024-10-13", "2024-10-19", "2026-10-24", "Synthetic frozen export provenance"]) assert.ok(details.includes(value));
      assert.match(details, /data-trend-replay="true"/);
      if (locale === "en") assert.match(details, /fetch time is unverified/);
    }
  }
});

test("legacy old observation windows are labelled historical without inventing replay provenance", () => {
  const intl = translations("en");
  const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": intl });
  const html = renderToStaticMarkup(React.createElement(MetaBar, { meta: {
    ...meta, observed_from: "2024-10-13", observed_to: "2024-10-19",
  } }));
  const summary = html.match(/<summary>([\s\S]*?)<\/summary>/)![1];
  assert.match(summary, /Historical estimate/);
  assert.doesNotMatch(summary, /2024-/);
  assert.match(html, /data measured 2024-10-13 to 2024-10-19/);
});
