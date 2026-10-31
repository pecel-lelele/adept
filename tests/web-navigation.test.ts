import test from "node:test";
import assert from "node:assert/strict";
import { journeyHref, safeReturn } from "../src/web/src/lib/navigation.ts";
import { activeItem, allItems, journeyStepCount, learnerWorkspace } from "../src/web/src/config/navigation.ts";

test("comparison is discoverable and active without changing the six numbered stages", () => {
  const item = activeItem(learnerWorkspace, "/app/pathway/compare");
  assert.equal(item?.key, "compare");
  assert.equal(item?.scenario, true);
  assert.equal(item?.step, undefined);
  assert.ok(allItems(learnerWorkspace).includes(item!));
  assert.equal(journeyStepCount(), 6);
  assert.equal(activeItem(learnerWorkspace, "/app/pathway")?.key, "plan");
});

test("preserves role and scenario without leaking snapshot replay or local filters", () => {
  const params = new URLSearchParams(
    "role=data-analyst&scenario=fast&snapshot_date=2026-10-13&max_cost_myr=0",
  );
  assert.equal(
    journeyHref("/app/progress", params),
    "/app/progress?scenario=fast&role=data-analyst",
  );
});
test("an explicit target role wins over previous context", () => {
  assert.equal(
    journeyHref(
      "/app/pathway?role=data-analyst",
      new URLSearchParams("role=old&scenario=fast"),
    ),
    "/app/pathway?role=data-analyst&scenario=fast",
  );
});
test("rejects external, protocol-relative, cross-mode and deceptive return URLs", () => {
  for (const input of [
    "https://evil.example/app",
    "//evil.example/app",
    "/org",
    "/application",
    "/app/\\evil",
    "/app/\n",
  ]) {
    assert.equal(safeReturn(input, "individual"), "/app");
  }
});
test("retains a valid deep link after demo entry", () => {
  assert.equal(
    safeReturn("/org/plan?role=data-analyst&scenario=fast", "organisation"),
    "/org/plan?role=data-analyst&scenario=fast",
  );
});

test("retains employee deep links and a manager's personal workspace", () => {
  assert.equal(safeReturn("/work/plan", "individual"), "/work/plan");
  assert.equal(safeReturn("/app/progress", "organisation"), "/app/progress");
  assert.equal(safeReturn("/workspaces", "individual"), "/app");
});
