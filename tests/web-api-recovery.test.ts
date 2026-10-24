import test from "node:test";
import assert from "node:assert/strict";
import { call, createApiClient } from "../src/web/src/lib/api/client.ts";

for (const status of [502, 503, 504]) {
  test(`GET recovers from one HTTP ${status}`, async (t) => {
    let attempts = 0;
    t.mock.method(globalThis, "fetch", async () => {
      attempts += 1;
      return attempts === 1
        ? new Response("unavailable", { status })
        : Response.json({ id: "synthetic-learner" });
    });
    const result = await call(createApiClient().GET("/api/v1/auth/me"));
    assert.equal(result.ok, true);
    assert.equal(attempts, 2);
  });
}

test("a persistent read outage stops after two attempts", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ error: { code: "storage_unavailable", message: "Try again" } }, { status: 503 }),
  );
  const result = await call(createApiClient().GET("/api/v1/auth/me"));
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.status, 503);
  assert.equal(fetch.mock.callCount(), 2);
});

test("failed writes are never repeated", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response(null, { status: 503 }));
  await call(createApiClient().POST("/api/v1/auth/login", {
    body: { email: "synthetic@example.test", password: "synthetic password" },
  }));
  assert.equal(fetch.mock.callCount(), 1);
});

test("authorization errors are not retried", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response(null, { status: 401 }));
  await call(createApiClient().GET("/api/v1/auth/me"));
  assert.equal(fetch.mock.callCount(), 1);
});

test("dropped reads still retry once", async (t) => {
  let attempts = 0;
  t.mock.method(globalThis, "fetch", async () => {
    if (++attempts === 1) throw new TypeError("connection lost");
    return Response.json({ id: "synthetic-learner" });
  });
  const result = await call(createApiClient().GET("/api/v1/auth/me"));
  assert.equal(result.ok, true);
  assert.equal(attempts, 2);
});
