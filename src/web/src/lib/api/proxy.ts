import { isIP } from "node:net";

import { proxyConfig } from "./proxy-config.ts";

type ProxyOptions = Omit<ReturnType<typeof proxyConfig>, "clientIpMode"> & {
  clientIpMode?: "trusted" | "best-effort"; apiUrl: string; timeoutMs?: number;
};
const FORWARDED_HEADERS = [
  "content-type", "accept", "authorization", "x-demo-user", "x-workspace", "x-sync-token",
  "origin", "access-control-request-method", "access-control-request-headers",
];
const HOP_HEADERS = new Set([
  "connection", "keep-alive", "transfer-encoding", "content-length", "content-encoding",
  "proxy-authenticate", "proxy-authorization", "te", "trailer", "upgrade",
]);

/** Use only the right-most entry; never accept a caller-prepended left-most identity. */
export function trustedClientIp(forwardedFor: string | null, hops: number, mode: "trusted" | "best-effort" = "trusted"): string | undefined {
  if (!forwardedFor || (hops <= 0 && mode === "trusted")) return undefined;
  const chain = forwardedFor.split(",").map((part) => part.trim());
  const address = chain.at(-1);
  return address && isIP(address) ? address : undefined;
}

/** Next.js is the only public HTTP server; FastAPI remains bound to loopback. */
export async function proxyRequest(request: Request, options?: ProxyOptions): Promise<Response> {
  const config: ProxyOptions = options ?? { ...proxyConfig(), apiUrl: process.env.API_URL ?? "http://127.0.0.1:8000" };
  const url = new URL(request.url);
  const health = ["/api/healthz", "/api/v1"].includes(url.pathname)
    && ["GET", "HEAD"].includes(request.method);
  const headers = new Headers();
  for (const key of FORWARDED_HEADERS) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  const address = trustedClientIp(request.headers.get("x-forwarded-for"), config.trustedHops, config.clientIpMode);
  // Platform health probes need no client identity and must not share auth rate buckets.
  if (!health && !address) {
    console.warn("Client address unavailable; forwarding without X-Real-IP.");
  }
  if (config.secret && address) {
    headers.set("x-real-ip", address);
    headers.set("x-internal-proxy-secret", config.secret);
  }
  const init: RequestInit & { duplex?: "half" } = {
    method: health ? "GET" : request.method,
    headers,
    cache: "no-store",
    // Auth is forwarded explicitly above. Disable fetch's implicit 401 challenge
    // handling, which cannot replay streamed uploads and can turn a 401 into a 502.
    credentials: "omit",
    redirect: "manual",
    signal: AbortSignal.any([request.signal, AbortSignal.timeout(config.timeoutMs ?? 35000)]),
  };
  if (!["GET", "HEAD"].includes(request.method) && request.body) {
    init.body = request.body;
    init.duplex = "half";
  }
  try {
    const upstream = await fetch(config.apiUrl + (health ? "/api/v1/health" : url.pathname + url.search), init);
    if (health) {
      const result = await upstream.json() as { status?: string; database?: string };
      const ready = upstream.ok && result.status === "ok" && result.database === "ok";
      return new Response(request.method === "HEAD" ? null : JSON.stringify(result), {
        status: ready ? 200 : 503,
        headers: { "content-type": "application/json", "cache-control": "no-store" },
      });
    }
    const responseHeaders = new Headers();
    const connectionHeaders = new Set((upstream.headers.get("connection") ?? "").split(",").map((part) => part.trim().toLowerCase()));
    upstream.headers.forEach((value, key) => {
      if (!HOP_HEADERS.has(key) && !connectionHeaders.has(key) && key !== "set-cookie") responseHeaders.set(key, value);
    });
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append("set-cookie", cookie);
    const body = request.method === "HEAD" || [204, 205, 304].includes(upstream.status) ? null : upstream.body;
    return new Response(body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ error: { code: "upstream_unavailable", message: "The API is unavailable. Try again shortly." } }, { status: health ? 503 : 502 });
  }
}
