"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

/** A missing workspace cookie is activated through an origin-checked POST, never a GET. */
export function WorkspaceActivation({ to, next }: { to: string; next: string }) {
  const form = useRef<HTMLFormElement>(null);
  const t = useTranslations("ui.workspace");
  useEffect(() => { form.current?.requestSubmit(); }, []);
  return <main className="a-page"><form ref={form} method="post" action="/api/workspace">
    <input type="hidden" name="to" value={to} />
    <input type="hidden" name="next" value={next} />
    <button className="a-btn" type="submit">{t("switch")}</button>
  </form></main>;
}
