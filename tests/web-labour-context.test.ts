import assert from "node:assert/strict";
import test from "node:test";
import { loadComponent, React, renderToStaticMarkup, translations } from "./harness/web-components.ts";

function find(node, predicate) {
  if (Array.isArray(node)) return node.map((child) => find(child, predicate)).find(Boolean);
  if (!React.isValidElement(node)) return undefined;
  return predicate(node) ? node : find(node.props.children, predicate);
}

test("month selection updates all rates, source dates and the fallback notice together", () => {
  let selected;
  const { MalaysiaContextPanel } = loadComponent("src/features/trends/components/MalaysiaContextPanel.tsx", {
    "next-intl": { ...translations(), useLocale: () => "en" },
    react: { useId: () => "synthetic-labour", useState: (initial) => [selected ?? initial, (value) => { selected = value; }] },
    "@/components/EstimateLabel": { EstimateLabel: () => null },
  });
  // Clearly synthetic observations exercise stored history without claiming real survey facts.
  const observations = [
    { observed_month: "2026-08-01", unemployment_rate: 2.9, participation_rate: 71, employment_population_ratio: 68.9,
      meta: { snapshot_date: "2026-08-01", is_estimate: false, is_fallback: true,
        sources: [{ name: "Synthetic survey", url: "https://example.test/survey", retrieved_at: "2026-10-30" }] } },
    { observed_month: "2026-07-01", unemployment_rate: 3.1, participation_rate: 70.5, employment_population_ratio: 68.3,
      meta: { snapshot_date: "2026-07-01", is_estimate: false, is_fallback: false,
        sources: [{ name: "Synthetic older survey", url: "https://example.test/older", retrieved_at: "2026-09-30" }] } },
  ];
  const tree = MalaysiaContextPanel({ observations });
  const select = find(tree, (node) => node.type === "select");
  assert.equal(select.props.disabled, false);
  assert.equal(select.props["aria-label"], "Month");
  const first = renderToStaticMarkup(tree);
  assert.match(first, /width:2.9%/);
  assert.match(first, /width:71%/);
  assert.match(first, /Showing last good snapshot from 2026-08-01/);
  select.props.onChange({ target: { value: "2026-07-01" } });
  const second = renderToStaticMarkup(MalaysiaContextPanel({ observations }));
  assert.match(second, /width:3.1%/);
  assert.match(second, /width:70.5%/);
  assert.match(second, /Synthetic older survey/);
  assert.match(second, /Retrieved 2026-09-30/);
  assert.doesNotMatch(second, /Showing last good snapshot/);
  assert.doesNotMatch(second, /Retrieved 2026-10-30/);
});
