/**
 * Validates a caller-supplied redirect value against the app's own origin.
 *
 * Returns the sanitised `pathname + search + hash` of the resolved URL when the
 * resolved origin exactly matches the app origin, or `fallback` otherwise.
 *
 * All of the following are rejected (resolve to `fallback`):
 *   - protocol-relative paths like `//attacker.example`
 *   - backslash variants `/\attacker.example`, `\\attacker.example`
 *   - absolute URLs with a foreign origin
 *   - `javascript:`, `data:`, and other non-http(s) schemes
 *   - tab / newline / control-character variants after URL decoding
 *   - empty or missing values
 *
 * Safe same-origin paths like `/`, `/dashboard`, and `/path?q=1#hash` pass through.
 *
 * @param next    - Raw value from the query parameter (may be empty / null).
 * @param origin  - The app's canonical public origin, e.g. "http://localhost:3000".
 * @param fallback - Returned when `next` is absent or rejected. Defaults to "/".
 */
export function getSafeRedirectPath(
  next: string | null | undefined,
  origin: string,
  fallback = "/",
): string {
  if (!next) return fallback;
  try {
    const resolved = new URL(next, origin);
    const appOrigin = new URL(origin).origin;
    if (resolved.origin !== appOrigin) return fallback;
    // Return only the path portion — never the raw user input string.
    const path = resolved.pathname + resolved.search + resolved.hash;
    // A same-origin absolute URL can have a // pathname. Emitting that pathname
    // as Location would make the browser interpret it as an external authority.
    if (new URL(path, origin).origin !== appOrigin) return fallback;
    return path;
  } catch {
    return fallback;
  }
}

