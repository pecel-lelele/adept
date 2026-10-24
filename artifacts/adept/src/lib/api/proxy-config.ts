/** Deployment-only validation; never infer trust from a caller's forwarded headers. */
export function proxyConfig(env: NodeJS.ProcessEnv = process.env) {
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
