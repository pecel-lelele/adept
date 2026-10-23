import express from "express";
import cookieParser from "cookie-parser";
import { actions, handlers, Redirect, requestContext } from "@workspace/adept-server";

const INTERNAL_API = "http://127.0.0.1:8000";
export const adept = express.Router();
adept.use(cookieParser());
adept.use((req, res, next) => {
  res.setHeader("Cache-Control", "no-store");
  // Same-origin mutation protection applies to both JSON and multipart requests.
  const origin = req.get("origin");
  const host = req.get("x-forwarded-host") ?? req.get("host");
  if (!["GET", "HEAD", "OPTIONS"].includes(req.method) && origin && new URL(origin).host !== host) {
    res.status(403).json({ error: "Cross-origin request rejected" }); return;
  }
  requestContext.run({ req, res }, next);
});
adept.get("/api/session", async (req, res) => {
  const token = req.cookies.adept_session;
  let account: any = null;
  if (token?.startsWith("v1.")) {
    const result = await fetch(INTERNAL_API + "/api/v1/auth/me", { headers: { "X-Demo-User": token } });
    if (result.ok) account = await result.json();
  }
  const allowed = (process.env.ADMIN_EMAILS ?? "").split(",").map(email => email.trim().toLowerCase()).filter(Boolean);
  const isAdmin = !!account && (allowed.length ? allowed.includes(account.email.toLowerCase()) : process.env.NODE_ENV !== "production");
  res.json({ authenticated: !!account, org: req.cookies.adept_org, locale: req.cookies.NEXT_LOCALE ?? "en", auth_mode: process.env.AUTH_MODE ?? "demo", is_admin: isAdmin });
});

async function webRequest(req: express.Request) {
  const protocol = req.get("x-forwarded-proto")?.split(",")[0] ?? req.protocol;
  const host = req.get("x-forwarded-host") ?? req.get("host");
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value) headers.set(key, Array.isArray(value) ? value.join(", ") : value);
  }
  const init: any = { method: req.method, headers };
  if (!["GET", "HEAD"].includes(req.method)) { init.body = req; init.duplex = "half"; }
  return new Request(`${protocol}://${host}${req.originalUrl}`, init);
}

adept.post("/api/rpc", async (req, res) => {
  try {
    const declared = Number(req.get("content-length"));
    if (!Number.isFinite(declared) || declared > 6 * 1024 * 1024) { res.sendStatus(413); return; }
    const form = await (await webRequest(req)).formData();
    const module = String(form.get("module") ?? "");
    const name = String(form.get("export") ?? "");
    const fn = Object.hasOwn(actions, module) && Object.hasOwn(actions[module], name) ? actions[module][name] : undefined;
    if (typeof fn !== "function") { res.sendStatus(404); return; }
    const encoded = JSON.parse(String(form.get("args") ?? "[]"));
    if (!Array.isArray(encoded) || encoded.length > 12) { res.sendStatus(400); return; }
    const args = encoded.map((arg, index) => {
      if (!arg?.$form) return arg === null ? undefined : arg;
      const result = new FormData();
      const prefix = `form:${index}:`;
      for (const [key, value] of form) if (key.startsWith(prefix)) result.append(key.slice(prefix.length), value);
      return result;
    });
    res.json({ result: await fn(...args) });
  } catch (error) {
    if (error instanceof Redirect) { res.json({ redirect: error.location }); return; }
    req.log.error({ err: error }, "Action failed");
    res.status(500).json({ error: "Unable to complete this action. Please try again." });
  }
});
for (const [path, handler] of Object.entries(handlers)) {
  adept.all(path, async (req, res) => {
    const fn = handler[req.method];
    if (!fn) { res.sendStatus(405); return; }
    const result = await fn(await webRequest(req));
    res.status(result.status);
    result.headers.forEach((value: string, key: string) => res.setHeader(key, value));
    res.send(Buffer.from(await result.arrayBuffer()));
  });
}
adept.use("/api/v1", async (req, res) => {
  const headers = new Headers();
  for (const key of ["content-type", "accept"]) { const value = req.get(key); if (value) headers.set(key, value); }
  const token = req.cookies.adept_session;
  if (token?.startsWith("v1.")) headers.set("X-Demo-User", token);
  const referer = req.get("referer");
  const page = referer ? new URL(referer).pathname : "";
  const workspace = /^\/(work|org)(\/|$)/.test(page) ? req.cookies.adept_org : "personal";
  if (workspace) headers.set("X-Workspace", workspace);
  const init: any = { method: req.method, headers, signal: AbortSignal.timeout(35000) };
  if (!["GET", "HEAD"].includes(req.method)) { init.body = req; init.duplex = "half"; }
  const upstream = await fetch(INTERNAL_API + req.originalUrl, init);
  res.status(upstream.status);
  upstream.headers.forEach((value, key) => { if (!["transfer-encoding", "content-length", "content-encoding"].includes(key)) res.setHeader(key, value); });
  res.send(Buffer.from(await upstream.arrayBuffer()));
});
