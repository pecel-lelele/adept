import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";

import { publicOrigin } from "../src/web/src/lib/api/proxy-config.ts";
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

test("logout refuses GET and cross-origin POST; successful revocation clears both cookies", async () => {
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
  runInNewContext(code, { module, exports: module.exports, URL, console, process: { env: {} }, require: (id: string) => ({
    "next/server": { NextResponse },
    "@/lib/auth/session": { SESSION_COOKIE: "session" },
    "@/lib/api/proxy-config": { publicOrigin: (r: Request) => publicOrigin(r, {}) },
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
  result = { ok: false, status: 503, code: "storage_unavailable" };
  assert.equal((await POST(request())).status, 303);
  assert.deepEqual(deleted, ["session", "org"]);
  deleted.length = 0;
  result = { ok: true, status: 204, code: "" };
  const response = await POST(request());
  assert.equal(response.status, 303);
  assert.equal(response.headers.get("location"), "/");
  assert.deepEqual(deleted, ["session", "org"]);
  assert.deepEqual(calls, ["/api/v1/auth/logout", "/api/v1/auth/logout"]);
  for (const [next, expected] of [
    ["/auth/login?mode=organisation#form", "/auth/login?mode=organisation#form"],
    ["/auth/signup?mode=organisation&role=team", "/auth/signup?mode=organisation&role=team"],
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
  for (const file of ["components/shell/Shell.tsx", "components/shell/Nav.tsx"]) {
    const source = readFileSync(new URL(`../src/web/src/${file}`, import.meta.url), "utf8");
    assert.match(source, /<form method="post" action="\/auth\/logout">/);
    assert.doesNotMatch(source, /href="\/auth\/logout"/);
  }
  const errorState = readFileSync(new URL("../src/web/src/components/ErrorState.tsx", import.meta.url), "utf8");
  assert.match(errorState, /<SignInAgainButton /);
  assert.doesNotMatch(errorState, /href="\/auth\/logout"/);
});

test("sign in again posts logout and returns to the current page after login", () => {
  const { SignInAgainButton } = loadComponent("src/components/SignInAgainButton.tsx", {
    "next/navigation": {
      usePathname: () => "/app/pathway",
      useSearchParams: () => new URLSearchParams("role=data_analyst&scenario=fast"),
    },
  });
  const { renderToStaticMarkup } = require("react-dom/server");
  const React = require("react");
  const html = renderToStaticMarkup(React.createElement(SignInAgainButton, { label: "Sign in again" }));
  assert.match(html, /<form[^>]*method="post"/);
  assert.doesNotMatch(html, /href="\/auth\/logout"/);
  const action = html.match(/action="([^"]+)"/)?.[1].replaceAll("&amp;", "&") ?? "";
  const url = new URL(action, "https://adept.example.test");
  assert.equal(url.pathname, "/auth/logout");
  const login = url.searchParams.get("next") ?? "";
  assert.equal(getSafeRedirectPath(login, "https://adept.example.test"), login);
  const back = new URL(login, "https://adept.example.test");
  assert.equal(back.pathname, "/auth/login");
  assert.equal(back.searchParams.get("next"), "/app/pathway?role=data_analyst&scenario=fast");
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
