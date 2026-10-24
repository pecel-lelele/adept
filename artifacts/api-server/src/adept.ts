import { isIP } from "node:net";
import { Readable } from "node:stream";
import express, { type Request } from "express";
import { privateApiUrl } from "./backend.ts";

export type ProxyConfig = { secret: string; trustedHops: number };

export function proxyConfig(env: NodeJS.ProcessEnv = process.env): ProxyConfig {
  const raw = env.TRUSTED_PROXY_HOPS ?? "0";
  const trustedHops = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isSafeInteger(trustedHops) || trustedHops > 32) {
    throw new Error("TRUSTED_PROXY_HOPS must be an integer between 0 and 32.");
  }
  const secret = env.PROXY_SHARED_SECRET ?? "";
  if (env.APP_ENV === "production" && (!secret.trim() || trustedHops === 0)) {
    throw new Error("Production requires PROXY_SHARED_SECRET and a verified positive TRUSTED_PROXY_HOPS count.");
  }
  return { secret, trustedHops };
}

function clientAddress(req: Request, trustedHops: number): string | undefined {
  if (trustedHops === 0) return req.socket.remoteAddress;
  const chain = (req.get("x-forwarded-for") ?? "").split(",").map((ip) => ip.trim());
  if (chain.length < trustedHops) return undefined;
  const address = chain[chain.length - trustedHops];
  return address && isIP(address) ? address : undefined;
}

/** Keep FastAPI's CORS, authentication and rate-limit boundaries across the public proxy. */
export function createAdeptRouter(config: ProxyConfig, upstreamUrl = privateApiUrl()) {
  const router = express.Router();
  router.use("/api/v1", async (req, res) => {
    const headers = new Headers();
    for (const key of [
      "content-type", "accept", "authorization", "x-demo-user", "x-workspace", "x-sync-token",
      "origin", "access-control-request-method", "access-control-request-headers",
    ]) {
      const value = req.get(key);
      if (value) headers.set(key, value);
    }
    // Ignore caller-supplied internal headers. Only this server may sign a client address.
    const address = clientAddress(req, config.trustedHops);
    if (config.trustedHops > 0 && !address) {
      res.status(400).json({ error: { code: "invalid_proxy_chain", message: "Client address unavailable." } });
      return;
    }
    if (config.secret && address) {
      headers.set("x-real-ip", address);
      headers.set("x-internal-proxy-secret", config.secret);
    }
    const init: RequestInit & { duplex?: "half" } = {
      method: req.method, headers, signal: AbortSignal.timeout(35000), redirect: "manual",
    };
    if (!["GET", "HEAD"].includes(req.method)) {
      init.body = Readable.toWeb(req) as ReadableStream<Uint8Array>;
      init.duplex = "half";
    }
    try {
      const upstream = await fetch(upstreamUrl + req.originalUrl, init);
      const body = Buffer.from(await upstream.arrayBuffer());
      res.status(upstream.status);
      upstream.headers.forEach((value, key) => {
        if (!["transfer-encoding", "content-length", "content-encoding", "connection"].includes(key)) {
          res.setHeader(key, value);
        }
      });
      res.send(body);
    } catch {
      res.status(502).json({ error: { code: "upstream_unavailable", message: "The API is unavailable. Try again shortly." } });
    }
  });
  return router;
}
