"use client";

import { useEffect, useState } from "react";

const TOAST_EVENT = "adept:progress-toast";
const TOAST_KEY = "adept:progress-toast";

/**
 * Triggers a toast notification that persists across Next.js Server Component re-renders.
 */
export function triggerProgressToast(message: string) {
  try {
    sessionStorage.setItem(TOAST_KEY, message);
  } catch {}
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: message }));
  }
}

/**
 * Toast notification container mounted at the ProgressView level.
 * Stays mounted even when a course item flips from incomplete to completed (replacing MarkDoneFlow with Undo).
 */
export function ProgressToast() {
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    // Check if a toast was queued in sessionStorage
    try {
      const stored = sessionStorage.getItem(TOAST_KEY);
      if (stored) {
        sessionStorage.removeItem(TOAST_KEY);
        setToast(stored);
      }
    } catch {}

    function onToast(e: Event) {
      const msg = (e as CustomEvent<string>).detail;
      if (msg) {
        try {
          sessionStorage.removeItem(TOAST_KEY);
        } catch {}
        setToast(msg);
      }
    }

    window.addEventListener(TOAST_EVENT, onToast);
    return () => window.removeEventListener(TOAST_EVENT, onToast);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!toast) return null;

  return (
    <div role="status" className="a-toast">
      {toast}
    </div>
  );
}
