/** Carry the same plan context between workspace routes. */
export function journeyHref(
  path: string,
  params: Pick<URLSearchParams, "get">,
): string {
  const url = new URL(path, "https://adept.invalid");
  for (const key of ["scenario", "role", "snapshot_date"]) {
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
  if (!value || /[\\\r\n]/.test(value)) return base;
  try {
    const url = new URL(value, "https://adept.invalid");
    return url.origin === "https://adept.invalid" &&
      (url.pathname === base || url.pathname.startsWith(base + "/"))
      ? url.pathname + url.search
      : base;
  } catch {
    return base;
  }
}
