/** Deployment-only validation; never infer trust from a caller's forwarded headers. */
export function proxyConfig(env: NodeJS.ProcessEnv = process.env): {
  secret: string; trustedHops: number; clientIpMode: "trusted" | "best-effort";
} {
  const raw = env.TRUSTED_PROXY_HOPS ?? "0";
  const trustedHops = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isSafeInteger(trustedHops) || trustedHops > 32) {
    throw new Error("TRUSTED_PROXY_HOPS must be an integer between 0 and 32.");
  }
  const secret = env.PROXY_SHARED_SECRET ?? "";
  const clientIpMode = env.PROXY_CLIENT_IP_MODE ?? "best-effort";
  if (clientIpMode !== "trusted" && clientIpMode !== "best-effort") {
    throw new Error("PROXY_CLIENT_IP_MODE must be trusted or best-effort.");
  }
  if (env.APP_ENV === "production" && !secret.trim()) {
    throw new Error("Production requires PROXY_SHARED_SECRET.");
  }
  if (clientIpMode === "trusted" && env.APP_ENV === "production" && trustedHops === 0) {
    throw new Error("Trusted client IP mode requires a positive TRUSTED_PROXY_HOPS.");
  }
  // Development callers cannot establish a forwarding boundary without configured hops.
  const mode = env.APP_ENV === "production" ? clientIpMode : "trusted";
  return { secret, trustedHops, clientIpMode: mode };
}

/**
 * The app's public origin for same-origin checks and redirects.
 *
 * WEB_ORIGIN wins whenever it is set (production requires it). Without it, only a local
 * development server falls back to the request's own Host; forwarded host headers are never
 * trusted, because a caller can set them. Returns undefined in production without WEB_ORIGIN.
 */
export function publicOrigin(request: Request, env: NodeJS.ProcessEnv = process.env): string | undefined {
  const configured = env.WEB_ORIGIN?.trim();
  if (configured) return configured;
  if (env.APP_ENV === "production" || env.NODE_ENV === "production") return undefined;
  const url = new URL(request.url);
  return `${url.protocol}//${request.headers.get("host") ?? url.host}`;
}

/**
 * True when a state-changing request comes from the app's own pages.
 *
 * Uses Fetch Metadata (`Sec-Fetch-Site`) when the browser sends it, otherwise an exact
 * `Origin` match, otherwise the `Referer` origin. Absent evidence fails closed.
 */
export function isSameOriginRequest(request: Request, origin: string): boolean {
  const site = request.headers.get("sec-fetch-site");
  if (site) return site === "same-origin" || site === "none";
  const sent = request.headers.get("origin");
  if (sent) return sent === origin;
  const referer = request.headers.get("referer");
  if (!referer) return false;
  try {
    return new URL(referer).origin === origin;
  } catch {
    return false;
  }
}
