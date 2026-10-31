import assert from "node:assert/strict";
import test from "node:test";

import { loadComponent, React, renderToStaticMarkup, resolveTree, translations } from "./harness/web-components.ts";

function jobsComponents(locale = "en", roleOpenings = {}) {
  const intl = translations(locale);
  const server = { "next-intl/server": { getTranslations: async (ns) => intl.useTranslations(ns) } };
  const item = loadComponent("src/features/jobs/components/OpeningItem.tsx", server);
  const fetched = [];
  const card = loadComponent("src/features/jobs/components/RoleOpeningsCard.tsx", {
    ...server,
    "next/link": { default: ({ href, children }) => React.createElement("a", { href }, children) },
    "@/components": { MetaBar: () => null },
    "@/components/Fold": {
      Fold: ({ meta, children }) => React.createElement("section", {}, React.createElement("p", {}, meta), children),
    },
    "../api": {
      fetchRoleOpenings: async (...args) => {
        fetched.push(args);
        return { ok: true, data: roleOpenings };
      },
    },
    "./OpeningItem": item,
  });
  return { ...item, ...card, fetched };
}

const opening = {
  id: "1",
  title: "Synthetic Analyst",
  employer: "Synthetic Employer",
  location: "Remote",
  work_mode: "remote",
  remote_scope: "Worldwide",
  malaysia_relevance: "remote_assumed_worldwide",
  url: "https://example.test/job",
  source_name: "Synthetic Board",
  last_seen: "2026-10-23",
  is_stale: false,
  skills: [],
};

async function render(OpeningItem, props) {
  return renderToStaticMarkup(await resolveTree(await OpeningItem(props)));
}

test("opening cards keep the employer and external action without feed clutter", async () => {
  const { OpeningItem } = jobsComponents();
  const html = await render(OpeningItem, { o: opening });
  assert.match(html, /Synthetic Employer · Remote \(Worldwide\)/);
  assert.doesNotMatch(html, /a-chip|via Synthetic Board/);
  assert.match(html, /href="https:\/\/example.test\/job"/);
});

test("Malaysia focus highlights work eligibility without dumping feed names", async () => {
  const { OpeningItem } = jobsComponents();
  const cases = [
    ["in_malaysia", "Kuala Lumpur", "up", "In Malaysia"],
    ["remote_explicit_my", "Remote", null, "Remote · open to Malaysia"],
    ["remote_assumed_worldwide", "Remote", "warn", "Remote · worldwide"],
  ];
  for (const [state, location, tone, label] of cases) {
    const o = { ...opening, location, malaysia_relevance: state };
    const html = await render(OpeningItem, { o, malaysiaFocus: true });
    assert.ok(html.includes(`Synthetic Employer · ${location}`), state);
    assert.ok(html.includes(label), state);
    assert.ok(html.includes(tone ? `class="a-chip" data-tone="${tone}"` : `class="a-chip">`), state);
    assert.doesNotMatch(html, /via Synthetic Board/);
    assert.ok(html.includes('href="https://example.test/job"'), state);
  }
});

test("counts stay split and leave out empty remote parts", async () => {
  const { placeCounts } = jobsComponents();
  assert.equal(
    await placeCounts({ in_malaysia: 4, remote_explicit_my: 1, remote_assumed_worldwide: 2 }),
    "4 in Malaysia · 1 remote open to Malaysia · 2 remote worldwide",
  );
  assert.equal(await placeCounts({ in_malaysia: 0, remote_explicit_my: 0, remote_assumed_worldwide: 3 }), "0 in Malaysia · 3 remote worldwide");
});

test("a role with no Malaysia-relevant opening says so only with Malaysia focus on", async () => {
  const empty = { open_count: 0, role_label: "Synthetic role", places: { in_malaysia: 0, remote_explicit_my: 0, remote_assumed_worldwide: 0 } };
  const { RoleOpeningsCard, fetched } = jobsComponents("en", empty);
  const focused = renderToStaticMarkup(
    await resolveTree(await RoleOpeningsCard({ roleId: "synthetic", scenario: "moderate", malaysiaFocus: true })),
  );
  assert.match(focused, /No live Malaysia-based or Malaysia-open opening for this role/);
  const plain = renderToStaticMarkup(await resolveTree(await RoleOpeningsCard({ roleId: "synthetic", scenario: "moderate" })));
  assert.match(plain, /No openings for Synthetic role right now/);
  assert.doesNotMatch(plain, /Malaysia/);
  assert.deepEqual(fetched.map((args) => args[3]), [true, false]);
});

test("the new strings are translated in Malay and Chinese", async () => {
  for (const [locale, label] of [["ms", "Jarak jauh · seluruh dunia"], ["zh", "远程 · 全球"]]) {
    const { OpeningItem } = jobsComponents(locale);
    assert.ok((await render(OpeningItem, { o: opening, malaysiaFocus: true })).includes(label), locale);
  }
});
