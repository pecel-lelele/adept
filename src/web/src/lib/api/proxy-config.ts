/** Deployment-only validation; never infer trust from a caller's forwarded headers. */
export function proxyConfig(env: NodeJS.ProcessEnv = process.env): {
  secret: string; trustedHops: number; clientIpMode: "trusted" | "best-effort"; logXffCount?: boolean;
} {
  const raw = env.TRUSTED_PROXY_HOPS ?? "0";
  const trustedHops = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isSafeInteger(trustedHops) || trustedHops > 32) {
    throw new Error("TRUSTED_PROXY_HOPS must be an integer between 0 and 32.");
  }
  const secret = env.PROXY_SHARED_SECRET ?? "";
  const clientIpMode = env.PROXY_CLIENT_IP_MODE ?? "best-effort";
  const logXffCount = env.PROXY_LOG_XFF_COUNT ?? "false";
  if (logXffCount !== "true" && logXffCount !== "false") {
    throw new Error("PROXY_LOG_XFF_COUNT must be true or false.");
  }
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
  return { secret, trustedHops, clientIpMode: mode, logXffCount: logXffCount === "true" };
}
