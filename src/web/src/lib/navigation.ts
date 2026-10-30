/** Carry scenario and target role between routes; snapshot replay is opt-in per link. */
export function journeyHref(
  path: string,
  params: Pick<URLSearchParams, "get">,
  sourcePath?: string,
): string {
  const url = new URL(path, "https://adept.invalid");
  for (const key of ["scenario", "role"]) {
    if (key === "role" && sourcePath && !/^\/app\/(pathway|progress|sdg|matches)(\/|$)/.test(sourcePath)) continue;
    const value = params.get(key);
    if (value && !url.searchParams.has(key)) url.searchParams.set(key, value);
  }
  return url.pathname + url.search;
}
export function safeReturn(
  value: string | null,
  mode: "individual" | "organisation",
): string {
  const base = mode === "organisation" ? "/org" : "/app";
  const roots = mode === "organisation" ? ["/org", "/app", "/work", "/admin"] : ["/app", "/work", "/admin"];
  if (!value || /[\\\r\n]/.test(value)) return base;
  try {
    const url = new URL(value, "https://adept.invalid");
    return url.origin === "https://adept.invalid" &&
      roots.some((root) => url.pathname === root || url.pathname.startsWith(root + "/"))
      ? url.pathname + url.search
      : base;
  } catch {
    return base;
  }
}
