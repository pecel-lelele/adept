"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

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

/**
 * CSS animates the page wrapper only. Server-rendered score/KPI text belongs to React:
 * changing it from a parent effect can race streamed child hydration and strand a route
 * transition. Query-only scenario changes keep the same wrapper.
 */
export function PageEnter({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className="a-page-enter">
      {children}
    </div>
  );
}
