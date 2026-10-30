import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("unused SkillBankPanel is removed", () => {
  assert.equal(
    existsSync(new URL("../src/web/src/features/core/components/SkillBankPanel.tsx", import.meta.url)),
    false,
  );
});

test("legacy insight styles are not loaded globally", () => {
  const layout = readFileSync(new URL("../src/web/src/app/layout.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(layout, /import\s+["']\.\/insight\.css["']/);
});
