import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const meta = {
  snapshot_date: "2026-10-20", scenario: "moderate", is_estimate: true,
  served_from: "fixture", is_fallback: true,
  sources: [{ name: "Synthetic source", url: "https://example.test", retrieved_at: "2026-10-19" }],
};

test("fallback snapshot notice is visible outside collapsed citations in every locale", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { MetaBar } = loadComponent("src/components/MetaBar.tsx", { "next-intl": translations(locale) });
    const html = renderToStaticMarkup(React.createElement(MetaBar, { meta }));
    assert.match(html, /role="status"/);
    assert.ok(html.match(/<summary>([\s\S]*?)<\/summary>/)?.[1].includes("Synthetic source"));
    assert.ok(html.indexOf('role="status"') < html.indexOf("<details"));
    assert.match(html.split("<details")[0], /2026-10-20/);
    if (locale === "en") assert.match(html, /Showing last good snapshot from 2026-10-20/);
    const live = renderToStaticMarkup(React.createElement(MetaBar, { meta: { ...meta, is_fallback: false } }));
    assert.doesNotMatch(live, /role="status"/);
  }
});
