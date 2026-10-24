import assert from "node:assert/strict";
import path from "node:path";
import { once } from "node:events";
import test, { type TestContext } from "node:test";
import express, { type Express } from "express";
import { createAdeptRouter, proxyConfig } from "../src/adept.ts";
import { proxyConfig as webProxyConfig } from "../../adept/src/lib/api/proxy-config.ts";
import { nativeLibraryEnv, privateApiPort, waitForApi } from "../src/backend.ts";

const secret = "synthetic-test-proxy-secret";

test("Nix startup finds PyMuPDF's native library and preserves existing search paths", () => {
  const library = path.resolve("synthetic-nix", "lib", "libstdc++.so.6");
  const env = { LD_LIBRARY_PATH: "existing-library-path" };
  assert.deepEqual(nativeLibraryEnv(env, false), env);
  const result = nativeLibraryEnv(env, true, () => library, () => true);
  assert.equal(result.LD_LIBRARY_PATH, `${path.dirname(library)}${path.delimiter}${env.LD_LIBRARY_PATH}`);
  assert.equal(env.LD_LIBRARY_PATH, "existing-library-path");
  assert.throws(() => nativeLibraryEnv(env, true, () => "libstdc++.so.6", () => true), /valid.*runtime/);
  assert.throws(() => nativeLibraryEnv(env, true, () => { throw new Error("no compiler"); }), /Add gcc/);
});

async function serve(t: TestContext, app: Express): Promise<string> {
  const server = app.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => { server.closeAllConnections(); server.close(); });
  const address = server.address();
  assert(address && typeof address !== "string");
  return `http://127.0.0.1:${address.port}`;
}

async function echoProxy(t: TestContext, trustedHops = 1): Promise<string> {
  const upstream = express();
  upstream.use(async (req, res) => {
    const chunks: Buffer[] = [];
    for await (const chunk of req) chunks.push(Buffer.from(chunk));
    res.json({ headers: req.headers, body: Buffer.concat(chunks).toString(), url: req.originalUrl });
  });
  const url = await serve(t, upstream);
  const app = express();
  app.use(createAdeptRouter({ secret, trustedHops }, url));
  return serve(t, app);
}

test("CORS preflight headers reach upstream and its policy response survives", async (t) => {
  const upstream = express();
  upstream.use((req, res) => {
    assert.equal(req.method, "OPTIONS");
    assert.equal(req.get("origin"), "https://allowed.example.test");
    assert.equal(req.get("access-control-request-method"), "POST");
    assert.equal(req.get("access-control-request-headers"), "authorization,content-type");
    res.setHeader("access-control-allow-origin", req.get("origin")!);
    res.setHeader("access-control-allow-methods", "POST");
    res.setHeader("vary", "Origin");
    res.status(204).end();
  });
  const app = express();
  app.use(createAdeptRouter({ secret, trustedHops: 0 }, await serve(t, upstream)));
  const response = await fetch(await serve(t, app) + "/api/v1/profile/questionnaire", {
    method: "OPTIONS",
    headers: { Origin: "https://allowed.example.test", "Access-Control-Request-Method": "POST",
      "Access-Control-Request-Headers": "authorization,content-type" },
  });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://allowed.example.test");
  assert.equal(response.headers.get("vary"), "Origin");
});

test("server signs the trusted right-hand client, ignoring forged internal headers", async (t) => {
  const url = await echoProxy(t);
  const response = await fetch(url + "/api/v1/profile/me?view=skills", { headers: {
    "x-forwarded-for": "198.51.100.99, 203.0.113.10", "x-real-ip": "192.0.2.55",
    "x-internal-proxy-secret": "attacker-value", origin: "https://allowed.example.test",
  } });
  const body = await response.json();
  assert.equal(body.headers["x-real-ip"], "203.0.113.10");
  assert.equal(body.headers["x-internal-proxy-secret"], secret);
  assert.equal(body.headers.origin, "https://allowed.example.test");
  assert.equal(body.url, "/api/v1/profile/me?view=skills");
});

test("direct connections ignore forwarded spoofing when no proxies are trusted", async (t) => {
  const response = await fetch(await echoProxy(t, 0) + "/api/v1/health", {
    headers: { "x-forwarded-for": "203.0.113.88", "x-real-ip": "203.0.113.88" },
  });
  const body = await response.json();
  assert.equal(body.headers["x-real-ip"], "127.0.0.1");
});

test("one visitor exhausting a login bucket does not throttle another visitor", async (t) => {
  const counts = new Map<string, number>();
  const upstream = express();
  upstream.use((req, res) => {
    assert.equal(req.get("x-internal-proxy-secret"), secret);
    const ip = req.get("x-real-ip")!;
    const count = (counts.get(ip) ?? 0) + 1;
    counts.set(ip, count);
    res.status(count > 1 ? 429 : 200).end();
  });
  const app = express();
  app.use(createAdeptRouter({ secret, trustedHops: 1 }, await serve(t, upstream)));
  const url = await serve(t, app) + "/api/v1/auth/login";
  const visit = (ip: string) => fetch(url, { headers: { "x-forwarded-for": ip } });
  assert.equal((await visit("203.0.113.10")).status, 200);
  assert.equal((await visit("203.0.113.10")).status, 429);
  assert.equal((await visit("203.0.113.20")).status, 200);
});

test("a missing or malformed trusted proxy address fails closed", async (t) => {
  const url = await echoProxy(t);
  for (const value of ["", "not-an-ip"]) {
    const response = await fetch(url + "/api/v1/health", { headers: { "x-forwarded-for": value } });
    assert.equal(response.status, 400);
  }
});

test("streamed upload body and authentication headers are preserved", async (t) => {
  const body = "--demo\r\nContent-Disposition: form-data; name=\"file\"\r\n\r\nSynthetic CV\r\n--demo--\r\n";
  const response = await fetch(await echoProxy(t) + "/api/v1/profile/cv", {
    method: "POST", body, headers: { "x-forwarded-for": "203.0.113.10",
      "content-type": "multipart/form-data; boundary=demo", authorization: "Bearer synthetic",
      "x-workspace": "synthetic-org" },
  });
  const result = await response.json();
  assert.equal(result.body, body);
  assert.equal(result.headers.authorization, "Bearer synthetic");
  assert.equal(result.headers["x-workspace"], "synthetic-org");
});

test("an unavailable upstream returns a bounded, sanitized failure", async (t) => {
  const app = express();
  app.use(createAdeptRouter({ secret, trustedHops: 0 }, "http://127.0.0.1:1"));
  const response = await fetch(await serve(t, app) + "/api/v1/health");
  assert.equal(response.status, 502);
  assert.equal((await response.json()).error.code, "upstream_unavailable");
});

test("web and API enforce the same production proxy configuration", () => {
  for (const config of [proxyConfig, webProxyConfig]) {
    assert.throws(() => config({ APP_ENV: "production" }), /Production requires/);
    assert.throws(() => config({ APP_ENV: "production", PROXY_SHARED_SECRET: secret }), /Production requires/);
    for (const value of ["-1", "1.5", "true", "33", "1junk"]) {
      assert.throws(() => config({ TRUSTED_PROXY_HOPS: value }), /integer/);
    }
    assert.deepEqual(config({ APP_ENV: "production", PROXY_SHARED_SECRET: secret, TRUSTED_PROXY_HOPS: "1" }),
      { secret, trustedHops: 1 });
  }
});

test("readiness rejects a reachable API whose database is unavailable", async (t) => {
  const upstream = express();
  upstream.use((_req, res) => res.json({ status: "ok", database: "unavailable" }));
  await assert.rejects(waitForApi(await serve(t, upstream), 150), /did not become healthy/);
});

test("readiness accepts a healthy API and database", async (t) => {
  const upstream = express();
  upstream.use((_req, res) => res.json({ status: "ok", database: "ok" }));
  await waitForApi(await serve(t, upstream), 1000);
  assert.equal(privateApiPort({ API_PORT: "8200" }), 8200);
  for (const value of ["bad", "0", "80", "65536"]) {
    assert.throws(() => privateApiPort({ API_PORT: value }), /API_PORT/);
  }
});
