"use client";

import { ArrowRight, Building2, CircleCheck, EyeOff, Users } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { joinOrgAction, type AuthState } from "../auth-actions";

/**
 * A signed-in learner joins an organisation with the code their manager or career centre
 * shared, consenting to share their profile and learning progress with the organisation.
 */
export function JoinView({ code = "" }: { code?: string }) {
  const t = useTranslations("ui.join");
  const tp = useTranslations("ui.page");
  const [state, action, pending] = useActionState<AuthState, FormData>(joinOrgAction, {});
  const joined = state.values?.joined;
  return (
    <div className="a-view">
      <header className="a-pagehead">
        <div style={{ minWidth: 0 }}>
          <span className="a-eyebrow is-square">{tp("joinEyebrow")}</span>
          <h1 className="a-h1">{t("title")}</h1>
          <p className="a-lead">{t("body")}</p>
        </div>
      </header>
      <div className="a-split">
        <section className="a-card a-join" aria-live="polite">
          {joined ? (
            <div className="a-join-done">
              <span className="a-join-icon is-done" aria-hidden>
                <CircleCheck size={22} />
              </span>
              <h2>{t("done", { org: joined })}</h2>
              <p className="a-muted">{tp("joinedBody")}</p>
              <a className="a-btn" href={`/api/workspace?to=${encodeURIComponent(state.values?.org_id ?? "")}`}>
                {t("openWorkspace", { org: joined })} <ArrowRight size={16} aria-hidden />
              </a>
              <Link className="a-link" href="/app">
                {tp("joinedCta")}
              </Link>
            </div>
          ) : (
            <form action={action} className="a-join-form">
              <span className="a-join-icon" aria-hidden>
                <Building2 size={22} />
              </span>
              <label className="a-field" htmlFor="join-code">
                {tp("joinCode")}
                <input
                  id="join-code"
                  className="a-input a-code-input"
                  name="code"
                  required
                  minLength={4}
                  maxLength={16}
                  autoCapitalize="characters"
                  autoComplete="off"
                  placeholder="ABCD1234"
                  defaultValue={state.values?.code ?? code}
                />
              </label>
              <label className="a-check">
                <input
                  type="checkbox"
                  name="consent"
                  required
                  defaultChecked={state.values?.consent === "on"}
                />
                <span>
                  <strong>{t("consent")}</strong>
                  <small>{t("consentHint")}</small>
                </span>
              </label>
              {state.error ? (
                <p className="a-notice" data-tone="error" role="alert">
                  {state.error}
                </p>
              ) : null}
              <button className="a-btn is-block" disabled={pending}>
                {t("cta")} <ArrowRight size={16} aria-hidden />
              </button>
            </form>
          )}
        </section>
        <aside className="a-card is-sage">
          <div className="a-card-head">
            <h2>{tp("joinShares")}</h2>
          </div>
          <ul className="a-joinfacts">
            <li>
              <Users size={16} aria-hidden /> {tp("joinFact1")}
            </li>
            <li>
              <EyeOff size={16} aria-hidden /> {tp("joinFact2")}
            </li>
            <li>
              <CircleCheck size={16} aria-hidden /> {tp("joinFact3")}
            </li>
          </ul>
        </aside>
      </div>
      {!joined ? (
        <p className="a-small a-muted" style={{ marginTop: "1.5rem", textAlign: "center" }}>
          Do you want to create an account for your team?{" "}
          <Link
            className="a-link"
            href="/auth/logout?next=/auth/signup?mode=organisation%26role=team"
          >
            Create team account
          </Link>
        </p>
      ) : null}
    </div>
  );
}
