import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import test from "node:test";

const require = createRequire(new URL("../src/web/package.json", import.meta.url));
const ts = require("typescript");
const { unstable_getResponseFromNextConfig } = require("next/experimental/testing/server");

function config(mode: string) {
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/next.config.ts", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  runInNewContext(code, {
    module, exports: module.exports,
    process: { env: { NODE_ENV: mode }, cwd: () => fileURLToPath(new URL("../src/web", import.meta.url)) },
    require: (id: string) => id === "next-intl/plugin" ? { default: () => (value) => value, __esModule: true } : require(id),
  });
  return module.exports.default;
}

test("Next.js applies security headers to sample page and API responses without blocking local hydration", async () => {
  for (const path of ["/about", "/app/matches?scenario=fast", "/api/assistant"]) {
    const response = await unstable_getResponseFromNextConfig({ url: `https://adept.example.test${path}`, nextConfig: config("production") });
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("x-frame-options"), "DENY");
    assert.equal(response.headers.get("strict-transport-security"), "max-age=31536000; includeSubDomains");
    const csp = response.headers.get("content-security-policy");
    assert.match(csp, /frame-ancestors 'none'/);
    assert.match(csp, /script-src 'self' 'unsafe-inline'/);
    assert.match(csp, /style-src 'self' 'unsafe-inline'/);
    assert.match(csp, /form-action 'self'/);
    assert.doesNotMatch(csp, /unsafe-eval|https:|\*/);
  }
  const development = await unstable_getResponseFromNextConfig({ url: "http://localhost:3000/app", nextConfig: config("development") });
  assert.match(development.headers.get("content-security-policy"), /'unsafe-eval'/);
});
