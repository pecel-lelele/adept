import assert from "node:assert/strict";
import { once } from "node:events";
import { createServer, type RequestListener } from "node:http";
import test, { type TestContext } from "node:test";

import { proxyRequest, trustedClientIp } from "../src/web/src/lib/api/proxy.ts";
import { proxyConfig } from "../src/web/src/lib/api/proxy-config.ts";

const secret = "synthetic-proxy-test-secret";

async function serve(t: TestContext, handler: RequestListener): Promise<string> {
  const server = createServer(handler).listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => { server.closeAllConnections(); server.close(); });
  const address = server.address();
  assert(address && typeof address !== "string");
  return `http://127.0.0.1:${address.port}`;
}

function request(path = "/api/v1/auth/login", init: RequestInit = {}) {
  return new Request("http://adept.example.test" + path, {
    ...init,
    headers: { "x-forwarded-for": "203.0.113.10", ...Object.fromEntries(new Headers(init.headers)) },
  });
}

test("CORS preflight, auth, query and workspace headers survive the Next.js proxy", async (t) => {
  const apiUrl = await serve(t, (req, res) => {
    res.setHeader("access-control-allow-origin", req.headers.origin ?? "");
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ method: req.method, url: req.url, headers: req.headers }));
  });
  const response = await proxyRequest(request("/api/v1/profile?scenario=fast", {
    method: "OPTIONS",
    headers: {
      origin: "https://allowed.example.test", authorization: "Bearer synthetic-token",
      "x-workspace": "synthetic-org", "access-control-request-method": "POST",
      "access-control-request-headers": "authorization,x-workspace",
    },
  }), { apiUrl, secret, trustedHops: 1 });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://allowed.example.test");
  const body = await response.json();
  assert.equal(body.method, "OPTIONS");
  assert.equal(body.url, "/api/v1/profile?scenario=fast");
  assert.equal(body.headers.authorization, "Bearer synthetic-token");
  assert.equal(body.headers["x-workspace"], "synthetic-org");
  assert.equal(body.headers["access-control-request-method"], "POST");
});

test("forged internal headers are discarded; only the trusted chain is signed", async (t) => {
  const apiUrl = await serve(t, (req, res) => res.end(JSON.stringify(req.headers)));
  const response = await proxyRequest(request(undefined, { headers: {
    "x-forwarded-for": "192.0.2.99, 203.0.113.7, 198.51.100.5",
    "x-real-ip": "192.0.2.123", "x-internal-proxy-secret": "forged",
  } }), { apiUrl, secret, trustedHops: 2 });
  const headers = await response.json();
  assert.equal(headers["x-real-ip"], "203.0.113.7");
  assert.equal(headers["x-internal-proxy-secret"], secret);
  assert.equal(headers["x-forwarded-for"], undefined);
});

test("development does not trust client-supplied forwarded identity", async (t) => {
  const apiUrl = await serve(t, (req, res) => res.end(JSON.stringify(req.headers)));
  const response = await proxyRequest(request(undefined, { headers: {
    "x-real-ip": "192.0.2.123", "x-internal-proxy-secret": "forged",
  } }), { apiUrl, secret, trustedHops: 0 });
  const headers = await response.json();
  assert.equal(headers["x-real-ip"], undefined);
  assert.equal(headers["x-internal-proxy-secret"], undefined);
});

test("one visitor cannot exhaust another visitor's login allowance", async (t) => {
  const hits = new Map<string, number>();
  const apiUrl = await serve(t, (req, res) => {
    assert.equal(req.headers["x-internal-proxy-secret"], secret);
    const ip = String(req.headers["x-real-ip"]);
    const count = (hits.get(ip) ?? 0) + 1;
    hits.set(ip, count);
    res.statusCode = count > 2 ? 429 : 200;
    res.end();
  });
  const config = { apiUrl, secret, trustedHops: 1 };
  for (const status of [200, 200, 429]) {
    const response = await proxyRequest(request(), config);
    assert.equal(response.status, status);
    await response.arrayBuffer();
  }
  const other = await proxyRequest(request(undefined, { headers: { "x-forwarded-for": "203.0.113.11" } }), config);
  assert.equal(other.status, 200);
  await other.arrayBuffer();
});

test("missing or malformed proxy chains fail closed on normal API routes", async () => {
  for (const value of [null, "spoofed", "203.0.113.1,"]) {
    const req = request();
    if (value === null) req.headers.delete("x-forwarded-for");
    else req.headers.set("x-forwarded-for", value);
    const response = await proxyRequest(req, { apiUrl: "http://127.0.0.1:1", secret, trustedHops: 1 });
    assert.equal(response.status, 400);
  }
  assert.equal(trustedClientIp("203.0.113.1", 2), undefined);
});

test("upload bodies, response cookies and status are preserved without hop headers", async (t) => {
  const apiUrl = await serve(t, async (req, res) => {
    let body = "";
    for await (const chunk of req) body += chunk;
    res.setHeader("set-cookie", ["one=1; HttpOnly", "two=2; HttpOnly"]);
    res.setHeader("connection", "close, x-internal-hop");
    res.setHeader("x-internal-hop", "remove-me");
    res.statusCode = 201;
    res.end(body);
  });
  const response = await proxyRequest(request("/api/v1/profile/cv", {
    method: "POST", body: "synthetic-upload-payload", headers: { "content-type": "application/octet-stream" },
  }), { apiUrl, secret, trustedHops: 1 });
  assert.equal(response.status, 201);
  assert.equal(await response.text(), "synthetic-upload-payload");
  assert.equal(response.headers.getSetCookie().length, 2);
  assert.equal(response.headers.get("connection"), null);
  assert.equal(response.headers.get("x-internal-hop"), null);
});

test("streamed login rejection remains 401 and is never replayed", async (t) => {
  let requests = 0;
  const apiUrl = await serve(t, async (req, res) => {
    requests++;
    for await (const chunk of req) void chunk;
    res.statusCode = 401;
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ error: "Invalid credentials" }));
  });
  const body = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(new TextEncoder().encode("synthetic-login")); controller.close(); },
  });
  const init: RequestInit & { duplex: "half" } = { method: "POST", body, duplex: "half" };
  const response = await proxyRequest(request(undefined, init), { apiUrl, secret, trustedHops: 1 });
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { error: "Invalid credentials" });
  assert.equal(requests, 1);
});

test("health aliases work without forwarded headers and verify database readiness", async (t) => {
  let database = "ok";
  const apiUrl = await serve(t, (req, res) => {
    assert.equal(req.url, "/api/v1/health");
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ status: "ok", database }));
  });
  for (const path of ["/api/healthz", "/api/v1"]) {
    const response = await proxyRequest(new Request("http://adept.example.test" + path), { apiUrl, secret, trustedHops: 1 });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    await response.json();
  }
  const head = await proxyRequest(new Request("http://adept.example.test/api/healthz", { method: "HEAD" }), { apiUrl, secret, trustedHops: 1 });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  database = "unavailable";
  const down = await proxyRequest(new Request("http://adept.example.test/api/healthz"), { apiUrl, secret, trustedHops: 1 });
  assert.equal(down.status, 503);
});

test("unavailable or timed-out upstreams return bounded, sanitized errors", async (t) => {
  const apiUrl = await serve(t, () => { /* Deliberately never answer. */ });
  const start = Date.now();
  const response = await proxyRequest(request(), { apiUrl, secret, trustedHops: 1, timeoutMs: 25 });
  assert.equal(response.status, 502);
  assert(Date.now() - start < 1000);
  assert(!JSON.stringify(await response.json()).includes(secret));
});

test("production still requires the shared secret and an explicit trusted hop count", () => {
  for (const env of [
    { APP_ENV: "production", TRUSTED_PROXY_HOPS: "1" },
    { APP_ENV: "production", PROXY_SHARED_SECRET: secret },
    { APP_ENV: "production", PROXY_SHARED_SECRET: "   ", TRUSTED_PROXY_HOPS: "1" },
    { TRUSTED_PROXY_HOPS: "-1" },
  ]) assert.throws(() => proxyConfig(env));
  assert.equal(proxyConfig({ APP_ENV: "production", PROXY_SHARED_SECRET: secret, TRUSTED_PROXY_HOPS: "1" }).trustedHops, 1);
});
