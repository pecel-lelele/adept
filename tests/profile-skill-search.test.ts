import assert from "node:assert/strict";
import test from "node:test";

import { canResolveSkill, createSessionResolver, filterCatalogueSkills } from "../src/web/src/features/profile/skill-search.ts";

test("manual search matches aliases directly without invoking a resolver", () => {
  const catalogue = [{ id: "excel", label: "Spreadsheet analysis", aliases: ["Microsoft Excel", "vlookup"] }];
  assert.deepEqual(filterCatalogueSkills(catalogue, "MICROSOFT excel", new Set()), catalogue);
  assert.deepEqual(filterCatalogueSkills(catalogue, "vlookup", new Set()), catalogue);
  assert.deepEqual(filterCatalogueSkills(catalogue, "vlookup", new Set(["excel"])), []);
});

test("short tokens and punctuation cannot trigger a request", () => {
  let calls = 0;
  const resolve = createSessionResolver(async () => { calls++; return { ok: true }; });
  for (const query of ["r", "c", "go", "   ", "x---", "sql", "x".repeat(81)]) {
    assert.equal(canResolveSkill(query), false);
    assert.equal(resolve(query), null);
  }
  assert.equal(calls, 0);
});

test("a slow typist changes only local filtering; explicit submissions share pending and empty results", async () => {
  let calls = 0;
  const resolve = createSessionResolver(async () => { calls++; return { ok: true, candidates: [] }; });
  for (const query of ["p", "py", "pyh", "pyht", "pyhto", "pyhton"]) {
    filterCatalogueSkills([], query, new Set());
  }
  assert.equal(calls, 0);
  const first = resolve(" Pyhton ");
  assert.equal(first, resolve("ＰＹＨＴＯＮ"));
  await first;
  assert.equal(first, resolve("pyhton"));
  assert.equal(calls, 1);
  const nextSession = createSessionResolver(async () => { calls++; return { ok: true }; });
  await nextSession("pyhton");
  assert.equal(calls, 2);
});

test("a failed request can be retried in the same session", async () => {
  let calls = 0;
  const resolve = createSessionResolver(async () => ({ ok: ++calls > 1 }));
  assert.equal((await resolve("pyhton"))?.ok, false);
  assert.equal((await resolve("pyhton"))?.ok, true);
});
