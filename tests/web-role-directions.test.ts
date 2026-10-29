import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

test("radar groups the existing RoleOption directions and keeps dated exploration explicit", () => {
  for (const locale of ["en", "ms", "zh"]) {
    const { RoleDirectionsCard } = loadComponent("src/features/trends/components/RoleDirectionsCard.tsx", {
      "next-intl": translations(locale), "@/components/MetaBar": { MetaBar: () => null },
      "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children) },
    });
    const props = {
      options: [
        { role_id: "synthetic-up", role_label: "Synthetic rising role", trend_direction: "rising", trend_signal: 0.2 },
        { role_id: "synthetic-down", role_label: "Synthetic declining role", trend_direction: "declining", trend_signal: -0.2 },
        { role_id: "synthetic-stable", role_label: "Synthetic stable role", trend_direction: "stable", trend_signal: 0 },
      ], meta: { scenario: "fast" },
    };
    const html = renderToStaticMarkup(React.createElement(RoleDirectionsCard, props));
    assert.match(html, /Synthetic rising role/);
    assert.match(html, /Synthetic declining role/);
    assert.doesNotMatch(html, /Synthetic stable role/);
    assert.match(html, /data-dir="rising"/);
    assert.match(html, /data-dir="declining"/);
    assert.doesNotMatch(html, /snapshot_date/);
    const dated = renderToStaticMarkup(React.createElement(RoleDirectionsCard, { ...props, snapshotDate: "2026-10-13" }));
    assert.match(dated, /snapshot_date=2026-10-13/);
  }
});
