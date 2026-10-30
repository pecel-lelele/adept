"use client";

import { ArrowRight, Building2, CircleCheck, EyeOff, Users } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { joinOrgAction, type AuthState } from "../auth-actions";

/**
 * A signed-in learner joins an organisation with the code their manager or career centre
 * shared. Joining needs consent; sharing skill levels with managers is a separate, optional
 * choice that starts unticked and can be changed later.
 */
export function JoinView({ code = "" }: { code?: string }) {
  const t = useTranslations("ui.join");
  const te = useTranslations("ui.apiErrors");
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
              <form method="post" action="/api/workspace"><input type="hidden" name="to" value={state.values?.org_id ?? ""} /><button className="a-btn" type="submit">
                {t("openWorkspace", { org: joined })} <ArrowRight size={16} aria-hidden />
              </button></form>
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
              <label className="a-check">
                <input type="checkbox" name="share_skills" defaultChecked={state.values?.share_skills === "on"} />
                <span>
                  <strong>{t("shareSkills")}</strong>
                  <small>{t("shareSkillsHint")}</small>
                </span>
              </label>
              <p className="a-small a-muted" style={{ margin: 0 }}>
                <Link className="a-link" href="/privacy">
                  {t("privacyLink")}
                </Link>
              </p>
              {state.error ? (
                <p className="a-notice" data-tone="error" role="alert">
                  {errorMessage(te, state.error)}
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
        <form method="post" action="/auth/logout?next=%2Fauth%2Fsignup%3Fmode%3Dorganisation%26role%3Dteam" className="a-small a-muted" style={{ marginTop: "1.5rem", textAlign: "center" }}>
          {t("teamAccountPrompt")}{" "}
          <button type="submit" className="a-link">
            {t("teamAccountCta")}
          </button>
          <br />
          {t("teamAccountSignOut")}
        </form>
      ) : null}
    </div>
  );
}
