"use client";

import { usePathname, useSearchParams } from "@/lib/next-compat/router";
import { useEffect, useState, type ReactNode } from "react";

const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * A thin bar at the top of the window from the moment an internal link is clicked until the
 * new route has rendered, so a slow server page never feels like a dead click.
 */
export function NavProgress() {
  const pathname = usePathname();
  const params = useSearchParams();
  const route = `${pathname}?${params.toString()}`;
  const [state, setState] = useState<"idle" | "loading" | "done">("idle");
  const [shown, setShown] = useState(route);

  // The route changed: finish the bar (derived during render, no effect needed).
  if (route !== shown) {
    setShown(route);
    if (state === "loading") setState("done");
  }

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      // Capture phase: next/link cancels the default click before it bubbles to document.
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as Element | null)?.closest?.("a");
      if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      setState("loading");
    };
    // GET forms (filters, team target role) navigate too.
    const onSubmit = (e: SubmitEvent) => {
      const form = e.target as HTMLFormElement | null;
      if (!form || (form.method || "get").toLowerCase() !== "get") return;
      if (new URL(form.action, window.location.href).origin === window.location.origin) setState("loading");
    };
    document.addEventListener("click", onClick, true);
    document.addEventListener("submit", onSubmit, true);
    return () => {
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("submit", onSubmit, true);
    };
  }, []);

  useEffect(() => {
    if (state === "idle") return;
    // "done" fades out; a "loading" that never finishes (navigation cancelled) gives up.
    const timer = window.setTimeout(() => setState("idle"), state === "done" ? 450 : 12000);
    return () => window.clearTimeout(timer);
  }, [state]);

  return <div className="a-navprogress" data-state={state} aria-hidden />;
}

/** Counts each key number up from zero when a page opens (skipped for reduced motion). */
function countUp(root: ParentNode) {
  if (reduced() || window.matchMedia("(max-width: 900px)").matches) return;
  root.querySelectorAll<HTMLElement>(".a-kpi-value strong, .a-fit strong").forEach((el) => {
    const text = el.textContent ?? "";
    const match = /^([^\d-]*)(-?\d[\d,]*(?:\.\d+)?)(.*)$/.exec(text);
    if (!match || el.dataset.counted === text) return;
    const [, before = "", num = "", after = ""] = match;
    const target = Number(num.replace(/,/g, ""));
    if (!Number.isFinite(target) || target === 0) return;
    const decimals = (num.split(".")[1] ?? "").length;
    const grouped = num.includes(",");
    const format = (v: number) => {
      const fixed = v.toFixed(decimals);
      return grouped ? Number(fixed).toLocaleString("en-MY", { minimumFractionDigits: decimals }) : fixed;
    };
    el.dataset.counted = text;
    const start = performance.now();
    const duration = 700;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = t < 1 ? `${before}${format(target * eased)}${after}` : text;
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

/**
 * Wraps each page: a short fade-and-rise entrance on every route change (keyed by path, so a
 * scenario or filter change in the query string does not replay it), then the number count-up.
 */
export function PageEnter({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  useEffect(() => {
    const main = document.getElementById("a-main");
    if (main) countUp(main);
  }, [pathname]);
  return (
    <div key={pathname} className="a-page-enter">
      {children}
    </div>
  );
}
