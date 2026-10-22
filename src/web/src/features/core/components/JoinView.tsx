"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { joinOrgAction, type AuthState } from "../auth-actions";

/** A signed-in learner joins an organisation with the code their manager shared. */
export function JoinView({ code = "" }: { code?: string }) {
  const t = useTranslations("ui.join");
  const [state, action, pending] = useActionState<AuthState, FormData>(joinOrgAction, {});
  const joined = state.values?.joined;
  return (
    <section className="a-card" style={{ maxWidth: 520 }}>
      <h2 style={{ marginTop: 0 }}>{t("title")}</h2>
      {joined ? (
        <div className="a-stack" style={{ gap: 12 }}>
          <p className="a-notice" data-tone="info" role="status">
            {t("done", { org: joined })}
          </p>
          <Link className="a-btn" href="/app">
            OK
          </Link>
        </div>
      ) : (
        <form action={action} className="a-stack" style={{ gap: 12 }}>
          <p className="a-muted" style={{ margin: 0 }}>
            {t("body")}
          </p>
          <input
            className="a-input"
            name="code"
            required
            minLength={4}
            maxLength={16}
            autoCapitalize="characters"
            defaultValue={state.values?.code ?? code}
            aria-label={t("title")}
            style={{ letterSpacing: 3, textTransform: "uppercase", fontWeight: 700 }}
          />
          {state.error ? (
            <p className="a-notice" data-tone="error" role="alert">
              {state.error}
            </p>
          ) : null}
          <button className="a-btn" disabled={pending}>
            {t("cta")}
          </button>
        </form>
      )}
    </section>
  );
}
