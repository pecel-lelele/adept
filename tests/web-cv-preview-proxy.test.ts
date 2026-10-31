import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";

const require = createRequire(new URL("../src/web/package.json", import.meta.url));
const ts = require("typescript");
const origin = "https://adept.example.test";
const body = JSON.stringify({ skills: [{ skill_id: "python", level: 3 }] });

function loadProxy(fetcher: typeof fetch) {
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/src/app/api/preview/route.ts", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInNewContext(code, {
    module, exports: module.exports, Response, URL, AbortSignal, TextDecoder, File,
    process: { env: { WEB_ORIGIN: origin } }, fetch: fetcher,
    require: (id: string) => {
      if (id === "@/lib/api/client") return { API_URL: "http://127.0.0.1:8000" };
      if (id === "@/lib/api/proxy") return { clientIpHeaders: () => ({}) };
      if (id === "@/lib/api/proxy-config") return { proxyConfig: () => ({}) };
      throw new Error(`Unexpected import ${id}`);
    },
  });
  return module.exports as { PUT: (request: Request) => Promise<Response> };
}

test("Save accepts JSON without Content-Length, as forwarded by streaming proxies", async () => {
  let forwarded = 0;
  const route = loadProxy(async (_url, options) => {
    forwarded++;
    assert.equal(options?.body, body);
    return Response.json({ top_role: { score: 0.6 } });
  });
  const request = new Request(`${origin}/api/preview`, {
    method: "PUT", headers: { origin, "content-type": "application/json" }, body,
  });
  assert.equal(request.headers.get("content-length"), null);
  const response = await route.PUT(request);
  assert.equal(response.status, 200);
  assert.equal(forwarded, 1);
});

for (const declared of [undefined, "2", "32769"]) {
  test(`Save enforces the actual byte limit (declared length: ${declared ?? "missing"})`, async () => {
    let forwarded = 0;
    const route = loadProxy(async () => { forwarded++; return Response.json({}); });
    const headers: Record<string, string> = { origin, "content-type": "application/json" };
    if (declared !== undefined) headers["content-length"] = declared;
    const response = await route.PUT(new Request(`${origin}/api/preview`, {
      method: "PUT", headers, body: " ".repeat(32769),
    }));
    assert.equal(response.status, 413);
    assert.equal(forwarded, 0);
  });
}

test("Save rejects malformed JSON before forwarding", async () => {
  const route = loadProxy(async () => { assert.fail("Malformed JSON must not reach the API"); });
  const response = await route.PUT(new Request(`${origin}/api/preview`, {
    method: "PUT", headers: { origin }, body: "{",
  }));
  assert.equal(response.status, 400);
});

test("Save still rejects a foreign origin", async () => {
  const route = loadProxy(async () => { assert.fail("Foreign origins must not reach the API"); });
  const response = await route.PUT(new Request(`${origin}/api/preview`, {
    method: "PUT", headers: { origin: "https://untrusted.example.test" }, body,
  }));
  assert.equal(response.status, 403);
});

test("Save preserves upstream errors without retrying or fabricating an outlook", async () => {
  let forwarded = 0;
  const route = loadProxy(async () => {
    forwarded++;
    return Response.json({ error: { code: "trend_unavailable" } }, { status: 503 });
  });
  const response = await route.PUT(new Request(`${origin}/api/preview`, {
    method: "PUT", headers: { origin }, body,
  }));
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: { code: "trend_unavailable" } });
  assert.equal(forwarded, 1);
});
