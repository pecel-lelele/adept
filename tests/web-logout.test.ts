import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";

import { isSameOriginRequest, publicOrigin } from "../src/web/src/lib/api/proxy-config.ts";
import { getSafeRedirectPath } from "../src/web/src/lib/auth/safeRedirect.ts";
import { loadComponent } from "./harness/web-components.ts";

const require = createRequire(new URL("../src/web/package.json", import.meta.url));
const ts = require("typescript");

test("the Next.js workspace gate admits v2 cookies and redirects legacy sessions", () => {
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/src/proxy.ts", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInNewContext(code, { module, exports: module.exports, Headers, URLSearchParams, require });
  const { NextRequest } = require("next/server");
  for (const path of ["/app/matches", "/work/plan", "/org/plan", "/admin/sources"]) {
    for (const version of ["v1", "v2"]) {
      const request = new NextRequest(`https://adept.example.test${path}`, { headers: {
        cookie: `adept_session=${version}.synthetic.9999999999.0.signature`,
      } });
      const response = module.exports.proxy(request);
      assert.equal(response.status, version === "v2" ? 200 : 303);
      if (version === "v1") assert.match(response.headers.get("location"), /\/auth\/login\?/);
      else assert.equal(response.headers.get("x-middleware-next"), "1");
    }
  }
});

test("the cookie reader forwards versioned sessions and rejects legacy or raw identities", async () => {
  let value = "v2.synthetic.9999999999.0.signature";
  const { getSessionToken } = loadComponent("src/lib/auth/session.ts", {
    "next/headers": { cookies: async () => ({ get: () => ({ value }) }) },
  });
  assert.equal(await getSessionToken({}), value);
  for (const invalid of ["v1.synthetic.9999999999.signature", "aisyah", ""]) {
    value = invalid;
    assert.equal(await getSessionToken({}), undefined);
  }
});

test("logout refuses GET and cross-origin POST; it always clears both cookies", async (t) => {
  const deleted: string[] = [];
  const calls: string[] = [];
  class NextResponse extends Response {
    cookies = { delete: (name: string) => deleted.push(name) };
  }
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/src/app/auth/logout/route.ts", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let result = { ok: true, status: 204, code: "" };
  const warning = t.mock.method(console, "warn", () => undefined);
  runInNewContext(code, { module, exports: module.exports, URL, console, process: { env: {} }, require: (id: string) => ({
    "next/server": { NextResponse },
    "@/lib/api/proxy-config": { publicOrigin: (request: Request) => publicOrigin(request, {}) },
    "@/lib/auth/session": { SESSION_COOKIE: "session" },
    "@/lib/auth/workspace": { ORG_COOKIE: "org" },
    "@/lib/auth/safeRedirect": { getSafeRedirectPath },
    "@/lib/api": { call: async () => result, getApi: async (options) => {
      assert.equal(options.workspace, "personal");
      return { POST: (path) => calls.push(path) };
    } },
  }[id]) });
  const { GET, POST } = module.exports;
  assert.equal(GET().status, 405);
  assert.equal(GET().headers.get("allow"), "POST");
  for (const origin of [undefined, "https://attacker.example.test"]) {
    assert.equal((await POST(new Request("https://adept.example.test/auth/logout", {
      method: "POST", headers: origin ? { origin } : {},
    }))).status, 403);
  }
  assert.deepEqual(calls, []);
  assert.deepEqual(deleted, []);
  const request = () => new Request("https://adept.example.test/auth/logout", { method: "POST", headers: { origin: "https://adept.example.test" } });
  // A failed revocation still signs this browser out, and is reported separately.
  result = { ok: false, status: 503, code: "storage_unavailable" };
  const failed = await POST(request());
  assert.equal(failed.status, 303);
  assert.equal(failed.headers.get("location"), "/");
  assert.equal(failed.headers.get("x-adept-logout"), "revoke-failed");
  assert.deepEqual(deleted, ["session", "org"]);
  assert.equal(warning.mock.calls.length, 1);
  deleted.length = 0;
  result = { ok: true, status: 204, code: "" };
  const response = await POST(request());
  assert.equal(response.status, 303);
  assert.equal(response.headers.get("location"), "/");
  assert.equal(response.headers.get("x-adept-logout"), null);
  assert.deepEqual(deleted, ["session", "org"]);
  assert.deepEqual(calls, ["/api/v1/auth/logout", "/api/v1/auth/logout"]);
  for (const [next, expected] of [
    ["/auth/login?mode=organisation#form", "/auth/login?mode=organisation#form"],
    ["/auth/signup?mode=organisation&role=team", "/auth/signup?mode=organisation&role=team"],
    // ErrorState links a stale session to logout, then back to login with its own next.
    ["/auth/login?next=%2Fapp%2Fmatches", "/auth/login?next=%2Fapp%2Fmatches"],
    ["https://attacker.example.test", "/"],
    ["//attacker.example.test", "/"],
    ["/.//attacker.example.test", "/"],
  ]) {
    const url = new URL(request().url);
    url.searchParams.set("next", next);
    const redirected = await POST(new Request(url, { method: "POST", headers: { origin: url.origin } }));
    assert.equal(redirected.status, 303);
    assert.equal(redirected.headers.get("location"), expected);
    assert.equal(new URL(redirected.headers.get("location"), url).origin, url.origin);
  }
  for (const file of ["components/shell/Shell.tsx", "components/shell/Nav.tsx", "components/ErrorState.tsx"]) {
    const source = readFileSync(new URL(`../src/web/src/${file}`, import.meta.url), "utf8");
    assert.match(source, /<form method="post" action="\/auth\/logout">/);
    assert.doesNotMatch(source, /href="\/auth\/logout"/);
  }
});

test("logout trusts WEB_ORIGIN, never a forwarded host, and fails closed in production", async () => {
  const forged = new Request("https://adept.example.test/auth/logout", { method: "POST", headers: {
    host: "adept.example.test", "x-forwarded-host": "attacker.example.test", "x-forwarded-proto": "https",
  } });
  assert.equal(publicOrigin(forged, {}), "https://adept.example.test");
  assert.equal(publicOrigin(forged, { WEB_ORIGIN: "https://adept-my.replit.app" }), "https://adept-my.replit.app");
  assert.equal(publicOrigin(forged, { APP_ENV: "production" }), undefined);
  assert.equal(publicOrigin(forged, { NODE_ENV: "production" }), undefined);
});

test("workspace switching changes the cookie only for Adept's own pages", async () => {
  const set: string[] = [];
  class NextResponse extends Response {
    cookies = { set: (name: string, value: string) => set.push(`${name}=${value}`) };
    static redirect(url: URL, status: number) {
      return new NextResponse(null, { status, headers: { location: url.toString() } });
    }
  }
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL("../src/web/src/app/api/workspace/route.ts", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let lookups = 0;
  runInNewContext(code, { module, exports: module.exports, URL, process: { env: {} }, require: (id: string) => ({
    "next/server": { NextResponse },
    "@/lib/api/proxy-config": { isSameOriginRequest, publicOrigin: (request: Request) => publicOrigin(request, {}) },
    "@/lib/auth/session": { getSessionToken: async () => "v2.synthetic.9999999999.0.signature" },
    "@/lib/auth/workspace": { ORG_COOKIE: "org", PERSONAL: "personal", isOrgId: (id: string) => id.startsWith("org-") },
    "@/lib/api/client": {
      createApiClient: () => ({ GET: () => undefined }),
      call: async () => {
        lookups += 1;
        return { ok: true, data: { workspaces: [{ kind: "org", id: "org-synthetic", role: "manager" }] } };
      },
    },
  }[id]) });
  const { GET, POST } = module.exports;
  const page = "https://adept.example.test";
  const get = (headers: Record<string, string>) =>
    GET(new Request(`${page}/api/workspace?to=org-synthetic`, { headers: { host: "adept.example.test", ...headers } }));
  for (const headers of [{ "sec-fetch-site": "same-origin" }, { "sec-fetch-site": "none" }, { referer: `${page}/app` }, { origin: page }]) {
    set.length = 0;
    const response = await get(headers);
    assert.equal(response.status, 303);
    assert.equal(response.headers.get("location"), `${page}/org`);
    assert.deepEqual(set, ["org=org-synthetic"]);
  }
  for (const headers of [
    { "sec-fetch-site": "cross-site" }, { "sec-fetch-site": "same-site" },
    { origin: "https://attacker.example.test" }, { referer: "https://attacker.example.test/x" }, {},
  ]) {
    set.length = 0;
    const before = lookups;
    const response = await get(headers);
    assert.equal(response.headers.get("location"), `${page}/app`);
    assert.deepEqual(set, []);
    assert.equal(lookups, before, "no membership lookup for a cross-site switch");
  }
  const form = (origin?: string) => {
    const body = new FormData();
    body.set("to", "org-synthetic");
    return new Request(`${page}/api/workspace`, { method: "POST", body, headers: { host: "adept.example.test", ...(origin ? { origin } : {}) } });
  };
  set.length = 0;
  assert.equal((await POST(form("https://attacker.example.test"))).status, 403);
  assert.equal((await POST(form())).status, 403);
  assert.deepEqual(set, []);
  const posted = await POST(form(page));
  assert.equal(posted.status, 303);
  assert.equal(posted.headers.get("location"), `${page}/org`);
  assert.deepEqual(set, ["org=org-synthetic"]);
});
