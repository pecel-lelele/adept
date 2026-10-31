import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

const module = loadComponent("src/features/trends/components/SignalExplorer.tsx", {
  "next-intl": translations("en"),
  "next/navigation": {
    usePathname: () => "/app/radar",
    useSearchParams: () => new URLSearchParams(),
    useRouter: () => ({ push() {} }),
  },
  "@/components/useBusy": { useBusy() {} },
});

const { SignalExplorer, pageItems } = module;

test("radar shows at most ten skills, clamps pages, and preserves sort inputs", () => {
  const items = Array.from({ length: 24 }, (_, n) => ({ id: n }));
  const plain = (value: unknown) => JSON.parse(JSON.stringify(value));
  assert.deepEqual(plain(pageItems(items, 1)), { items: items.slice(0, 10), page: 1, pages: 3 });
  assert.deepEqual(plain(pageItems(items, 2)), { items: items.slice(10, 20), page: 2, pages: 3 });
  assert.deepEqual(plain(pageItems(items, 99)), { items: items.slice(20), page: 3, pages: 3 });
  assert.deepEqual(plain(pageItems([], 8)), { items: [], page: 1, pages: 1 });
  assert.deepEqual(pageItems(items, -1).page, 1);
  assert.equal(items.length, 24, "pagination does not mutate the catalogue-backed snapshot");
});

test("radar pages stay labelled, mobile metrics remain named, and no rows leak", () => {
  const items = Array.from({ length: 23 }, (_, n) => ({
    skill_id: `synthetic-skill-${n}`,
    skill_label: `Synthetic skill ${n}`,
    velocity_moderate: 23 - n,
    velocity_fast: 23 - n,
    direction_moderate: "rising",
    direction_fast: "rising",
    automation_exposure: 0.5,
    labor_decay_source_note: "Synthetic test evidence only",
  }));
  const html = renderToStaticMarkup(React.createElement(SignalExplorer, {
    items, scenario: "moderate", dates: [],
  }));
  assert.equal((html.match(/class="a-row"/g) ?? []).length, 10);
  assert.match(html, /Page 1 of 3/);
  assert.match(html, /Previous<\/button>/);
  assert.match(html, /Next<\/button>/);
  assert.ok(html.includes("Signal") && html.includes("Exposure score"));
  assert.doesNotMatch(html, /Synthetic skill 10/);
  const css = readFileSync("src/web/src/app/adept.css", "utf8");
  assert.match(css, /@media \(max-width: 760px\)[\s\S]*?\.a-shell \.a-mobile-metric-label \{ display: block/);
});
