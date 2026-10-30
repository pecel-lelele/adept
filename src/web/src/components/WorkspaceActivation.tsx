"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

/**
 * A missing workspace cookie is activated through an origin-checked POST, never a GET.
 * Auto-submit happens once per target: if the browser refuses the cookie, a second load
 * shows the button and an explanation instead of reloading forever.
 */
export function WorkspaceActivation({ to, next }: { to: string; next: string }) {
  const form = useRef<HTMLFormElement>(null);
  const t = useTranslations("ui.workspace");
  const note = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const key = `adept-activate:${to}`;
    let seen = false;
    try {
      seen = window.sessionStorage.getItem(key) !== null;
      if (!seen) window.sessionStorage.setItem(key, "1");
    } catch {
      // Storage unavailable: still submit once per mount, never loop on reload.
    }
    if (seen) {
      if (note.current) note.current.hidden = false;
    }
    else form.current?.requestSubmit();
  }, [to]);
  return <main className="a-page"><form ref={form} method="post" action="/api/workspace">
    <input type="hidden" name="to" value={to} />
    <input type="hidden" name="next" value={next} />
    <p ref={note} role="status" hidden>{t("activateRetry")}</p>
    <button className="a-btn" type="submit">{t("switch")}</button>
  </form></main>;
}
