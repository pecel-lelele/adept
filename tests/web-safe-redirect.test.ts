import test from "node:test";
import assert from "node:assert/strict";
import { getSafeRedirectPath } from "../src/web/src/lib/auth/safeRedirect.ts";

const origin = "https://adept.example";

test("logout rejects external destinations, including reserialized same-origin URLs", () => {
  for (const raw of [
    "//attacker.example",
    "/\\attacker.example",
    "\\\\attacker.example",
    "https://attacker.example",
    "https://adept.example.attacker.example",
    "javascript:alert(1)",
    "data:text/html,hello",
    "/\t/attacker.example",
    "/\n/attacker.example",
    "https://adept.example//attacker.example",
    "https://adept.example/\\attacker.example",
    "/.//attacker.example",
    "/%2e//attacker.example",
    "https://[invalid",
    "",
    null,
    undefined,
  ]) {
    const destination = getSafeRedirectPath(raw, origin);
    assert.equal(destination, "/", String(raw));
    // Check how a browser resolves the returned Location header.
    assert.equal(new URL(destination, origin).origin, origin);
  }
});

test("logout preserves same-origin paths, query strings and fragments", () => {
  for (const [raw, expected] of [
    ["/", "/"],
    ["/auth/signin?mode=team#form", "/auth/signin?mode=team#form"],
    ["https://adept.example/app?tab=skills", "/app?tab=skills"],
    ["/app?next=https://attacker.example", "/app?next=https://attacker.example"],
    ["/app//profile", "/app//profile"],
  ]) {
    assert.equal(getSafeRedirectPath(raw, origin), expected);
  }
});
