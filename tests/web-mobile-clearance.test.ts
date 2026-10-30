import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("mobile main content and its final disclaimer clear Adi and the tab bar including safe areas", () => {
  const css = readFileSync(new URL("../src/web/src/app/adept.css", import.meta.url), "utf8");
  const adi = readFileSync(new URL("../src/web/src/app/adi.css", import.meta.url), "utf8");
  const breakpoint = "@media (max-width: 900px)";
  const mobile = css.slice(css.indexOf(breakpoint));
  const assistant = adi.slice(adi.indexOf(breakpoint));
  const offset = Number(assistant.match(/bottom:\s*calc\(var\(--a-tab-h, 64px\) \+ (\d+)px \+ env\(safe-area-inset-bottom\)\)/)[1]);
  const height = Number(assistant.match(/\.adi-launch\s*\{[^}]*height:\s*(\d+)px/)[1]);
  for (const selector of ["a-main", "a-foot"]) {
    const rule = mobile.match(new RegExp(`\\.${selector}\\s*\\{([^}]+)\\}`))[1];
    const clearance = Number(rule.match(/calc\(var\(--a-tab-h\) \+ (\d+)px \+ env\(safe-area-inset-bottom\)\)/)[1]);
    assert.ok(clearance >= 80);
    for (const safeArea of [0, 20, 34]) {
      for (const tabHeight of [64, 72]) {
        const contentBottomInset = tabHeight + safeArea + clearance;
        const launcherTopInset = tabHeight + safeArea + offset + height;
        assert.ok(contentBottomInset >= launcherTopInset + 16, `${selector}: final content overlaps the launcher`);
      }
    }
  }
});
