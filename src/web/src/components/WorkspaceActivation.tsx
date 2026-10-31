"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

/**
 * A missing workspace cookie is activated through an origin-checked POST, never a GET.
 * If the browser refuses the cookie, the redirect lands here again straight away: a repeat
 * within RETRY_WINDOW_MS shows the button and an explanation instead of reloading forever.
 * Later activations (for example after signing in again) still submit automatically.
 */
const RETRY_WINDOW_MS = 15_000;

export function WorkspaceActivation({ to, next }: { to: string; next: string }) {
  const form = useRef<HTMLFormElement>(null);
  const t = useTranslations("ui.workspace");
  const note = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    // A real loop repeats the same workspace and destination; a different page is a new activation.
    const key = `adept-activate:${to}:${next}`;
    let looping = false;
    try {
      const last = Number(window.sessionStorage.getItem(key));
      looping = Number.isFinite(last) && last > 0 && Date.now() - last < RETRY_WINDOW_MS;
      if (!looping) window.sessionStorage.setItem(key, String(Date.now()));
    } catch {
      // Storage unavailable: still submit once per mount.
    }
    if (looping) {
      if (note.current) note.current.hidden = false;
    }
    else form.current?.requestSubmit();
  }, [to, next]);
  return <main className="a-page"><form ref={form} method="post" action="/api/workspace">
    <input type="hidden" name="to" value={to} />
    <input type="hidden" name="next" value={next} />
    <p ref={note} role="status" hidden>{t("activateRetry")}</p>
    <button className="a-btn" type="submit">{t("switch")}</button>
  </form></main>;
}
