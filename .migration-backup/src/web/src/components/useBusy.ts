"use client";

import { useEffect } from "react";

/**
 * While a control re-fetches the current page (AI pace, snapshot, UN Goals weight, filters),
 * mark the document busy: the top progress bar runs and the page content dims until the new
 * data arrives, so the click visibly did something.
 */
export function useBusy(pending: boolean) {
  useEffect(() => {
    const root = document.documentElement;
    if (pending) root.setAttribute("data-busy", "");
    else root.removeAttribute("data-busy");
    return () => root.removeAttribute("data-busy");
  }, [pending]);
}
