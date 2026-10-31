import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import * as scenario from "../src/web/src/lib/scenario.ts";
import { loadComponent } from "./harness/web-components.ts";

for (const route of ["pathway", "progress"]) {
  test(`${route} with no selected role sends the learner to ranked roles`, async () => {
    let target = "";
    const { default: Page } = loadComponent(`src/app/app/${route}/page.tsx`, {
      "@/components": { ErrorState: () => null },
      "@/features/pathway": { fetchPlanStatus: async () => ({ ok: true, data: { saved: null } }) },
      "@/lib/scenario": scenario,
      "next/navigation": { redirect: (url: string) => { target = url; throw new Error("Synthetic redirect"); } },
    });
    await assert.rejects(() => Page({ searchParams: Promise.resolve({ scenario: "fast", snapshot_date: "2026-10-13" }) }), /Synthetic redirect/);
    assert.equal(target, `/app/matches?scenario=fast&choose_role=1${route === "pathway" ? "&snapshot_date=2026-10-13" : ""}`);
  });
}

test("the comparison screen and route implementation are removed", () => {
  assert.equal(existsSync("src/web/src/features/pathway/components/CompareRolesView.tsx"), false);
  assert.equal(existsSync("src/web/src/app/app/pathway/compare/page.tsx"), false);
});
