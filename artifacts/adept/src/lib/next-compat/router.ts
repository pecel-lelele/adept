import { useMemo, useSyncExternalStore } from "react";
import { navigate as wouterNavigate } from "wouter/use-browser-location";
import { useLocation, useSearch } from "wouter";

/** Router base without trailing slash ("" when mounted at root). */
export const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

/** Absolute browser URL for an app path. */
export function withBase(href: string): string {
  return href.startsWith("/") && !href.startsWith("//") ? BASE + href : href;
}

/** Paths served by the backend, not the SPA: always do a full page load. */
function isServerPath(path: string): boolean {
  return /^\/(api)(\/|$|\?)/.test(path);
}

export function navigate(href: string, options: { replace?: boolean; scroll?: boolean } = {}): void {
  if (/^[a-z]+:/i.test(href) || isServerPath(href)) {
    if (options.replace) window.location.replace(withBase(href));
    else window.location.assign(withBase(href));
    return;
  }
  wouterNavigate(withBase(href), { replace: options.replace });
  const hash = href.includes("#") ? href.slice(href.indexOf("#") + 1) : "";
  if (hash) {
    requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView());
  } else if (options.scroll !== false) {
    window.scrollTo(0, 0);
  }
}

/* ---- refresh generation (stands in for server re-rendering / revalidatePath) ---- */
let generation = 0;
const listeners = new Set<() => void>();
export function getGeneration(): number {
  return generation;
}
export function refresh(): void {
  generation += 1;
  listeners.forEach((l) => l());
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function useGeneration(): number {
  return useSyncExternalStore(subscribe, getGeneration, getGeneration);
}

/* ---- redirect / notFound ---- */
export class RedirectError extends Error {
  constructor(public url: string) {
    super(`Redirect to ${url}`);
  }
}
export class NotFoundError extends Error {
  constructor() {
    super("Not found");
  }
}
export function redirect(url: string): never {
  throw new RedirectError(url);
}
export function notFound(): never {
  throw new NotFoundError();
}

/** Current app path (without base). */
export function currentPath(): string {
  const path = window.location.pathname;
  return BASE && path.startsWith(BASE) ? path.slice(BASE.length) || "/" : path;
}

/* ---- hooks mirroring next/navigation ---- */
export function useRouter() {
  return useMemo(
    () => ({
      push: (href: string, opts?: { scroll?: boolean }) => navigate(href, { scroll: opts?.scroll }),
      replace: (href: string, opts?: { scroll?: boolean }) => navigate(href, { replace: true, scroll: opts?.scroll }),
      refresh: () => refresh(),
      back: () => window.history.back(),
      forward: () => window.history.forward(),
    }),
    [],
  );
}
export function usePathname(): string {
  return useLocation()[0];
}
export function useSearchParams(): URLSearchParams {
  const search = useSearch();
  return useMemo(() => new URLSearchParams(search), [search]);
}
