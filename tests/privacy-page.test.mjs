import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const base = new URL("../src/web/", import.meta.url);
const messages = (locale) => JSON.parse(readFileSync(new URL(`messages/${locale}/privacy.json`, base), "utf8"));

test("privacy has a public route", () => {
  assert.ok(existsSync(new URL("src/app/privacy/page.tsx", base)));
});

for (const locale of ["en", "ms", "zh"]) {
  test(`privacy notice contains the required disclosures in ${locale}`, () => {
    const notice = messages(locale);
    for (const section of ["controller", "purposes", "providers", "transfers", "retention", "rights"]) {
      assert.ok(notice[section].title.length > 0);
      assert.ok(notice[section].body.length > 0);
    }
    assert.deepEqual(Object.keys(notice).sort(), Object.keys(messages("en")).sort());
    assert.notEqual(notice.title, "");
  });
}
