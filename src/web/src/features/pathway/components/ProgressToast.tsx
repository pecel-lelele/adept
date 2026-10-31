"use client";

import { useEffect, useSyncExternalStore } from "react";

const TOAST_EVENT = "adept:progress-toast";
const TOAST_KEY = "adept:progress-toast";
let memoryToast: string | null | undefined;

function getToast(): string | null {
  if (memoryToast !== undefined) return memoryToast;
  try {
    return sessionStorage.getItem(TOAST_KEY) || null;
  } catch {
    return null;
  }
}

function getServerToast(): null {
  return null;
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(TOAST_EVENT, onChange);
  return () => window.removeEventListener(TOAST_EVENT, onChange);
}

/** Queue feedback across revalidation, including when browser storage is unavailable. */
export function triggerProgressToast(message: string) {
  memoryToast = message;
  try {
    sessionStorage.setItem(TOAST_KEY, message);
  } catch {}
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: message }));
  }
}

function dismissToast() {
  memoryToast = null;
  try {
    sessionStorage.removeItem(TOAST_KEY);
  } catch {}
  window.dispatchEvent(new CustomEvent(TOAST_EVENT));
}

/** Remains mounted when a completed course replaces its MarkDoneFlow with Undo. */
export function ProgressToast() {
  const toast = useSyncExternalStore(subscribe, getToast, getServerToast);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(dismissToast, 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!toast) return null;

  return (
    <div role="status" className="a-toast">
      {toast}
    </div>
  );
}
