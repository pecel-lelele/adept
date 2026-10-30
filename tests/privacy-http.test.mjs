import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const origin = new URL(process.env.ADEPT_PRIVACY_TEST_ORIGIN ?? "http://127.0.0.1:3107");
assert.equal(origin.hostname, "127.0.0.1", "Only a loopback test server is permitted");

for (const locale of ["en", "ms", "zh"]) {
  test(`/privacy renders ${locale} with HTTP 200`, async () => {
    const messages = JSON.parse(readFileSync(
      new URL(`../src/web/messages/${locale}/privacy.json`, import.meta.url), "utf8",
    ));
    const response = await fetch(new URL("/privacy", origin), {
      headers: { cookie: `NEXT_LOCALE=${locale}` },
      redirect: "manual",
      signal: AbortSignal.timeout(15000),
    });
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.ok(html.includes(`<html lang="${locale}"`));
    assert.ok(html.includes(messages.title));
    for (const section of ["controller", "purposes", "providers", "transfers", "retention", "rights"]) {
      assert.ok(html.includes(messages[section].title));
    }
    assert.ok(html.includes('href="/privacy"'));
  });
}
