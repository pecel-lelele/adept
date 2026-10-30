"use client";

import { Download, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActionState, useState } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { deleteAccountAction, type AuthState } from "../auth-actions";

/** "Your data": download everything stored about you, or delete the account for good. */
export function AccountDataCard() {
  const t = useTranslations("ui.account");
  const te = useTranslations("ui.apiErrors");
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState<AuthState, FormData>(deleteAccountAction, {});
  return (
    <section className="a-card" aria-labelledby="account-data-title">
      <h2 id="account-data-title" style={{ marginTop: 0 }}>
        {t("title")}
      </h2>
      <p className="a-small a-muted">
        {t("body")}{" "}
        <a className="a-link" href="/privacy">
          {t("privacyLink")}
        </a>
      </p>
      <div className="a-hero-actions">
        <a className="a-btn is-ghost is-small" href="/api/account/export" download>
          <Download size={15} aria-hidden /> {t("export")}
        </a>
        <button type="button" className="a-btn is-ghost is-small" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
          <Trash2 size={15} aria-hidden /> {t("delete")}
        </button>
      </div>
      {open ? (
        <form action={action} className="a-stack" style={{ marginTop: 16, display: "grid", gap: 10 }}>
          <p className="a-small" style={{ margin: 0 }}>
            {t("deleteWarning")}
          </p>
          <label className="a-field">
            <span>{t("password")}</span>
            <input className="a-input" type="password" name="password" autoComplete="current-password" required />
          </label>
          <label className="a-small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" name="confirm" required /> {t("confirm")}
          </label>
          {state.error ? (
            <p className="a-notice" data-tone="error" role="alert">
              {errorMessage(te, state.error)}
            </p>
          ) : null}
          <button type="submit" className="a-btn is-dark is-small" disabled={pending}>
            {pending ? t("deleting") : t("deleteForever")}
          </button>
        </form>
      ) : null}
    </section>
  );
}
