"use client";

import { Building2, UserRound } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useActionState, useState } from "react";

import { BrandLogo } from "@/components/shell/Brand";
import { OrgScene } from "@/components/viz/OrgScene";
import { PathScene } from "@/components/viz/PathScene";

import { loginAction, signupAction, type AuthState } from "../auth-actions";

type Page = "login" | "signup";

/** Real sign-up and sign-in. Every account and organisation is stored in PostgreSQL. */
export function AuthView({ page }: { page: Page }) {
  const t = useTranslations("ui.auth");
  const tl = useTranslations("ui.landing");
  const params = useSearchParams();
  const next = params.get("next") ?? "";
  const [state, action, pending] = useActionState<AuthState, FormData>(
    page === "signup" ? signupAction : loginAction,
    {},
  );
  const values = state.values ?? {};
  const [workspace, setWorkspace] = useState<"individual" | "organisation">(
    (values.workspace ?? params.get("mode")) === "organisation" ? "organisation" : "individual",
  );
  const team = workspace === "organisation";
  const query = next ? `?next=${encodeURIComponent(next)}` : "";

  return (
    <main className="a-page" data-mode={team ? "organisation" : "individual"}>
      <header className="a-page-top">
        <BrandLogo href="/" />
        <nav>
          <Link href="/try">{tl("try")}</Link>
        </nav>
      </header>
      <div className="a-auth">
        <section className="a-auth-card" aria-labelledby="auth-title">
          <div className="a-tabswitch" role="tablist">
            <Link href={`/auth/login${query}`} aria-current={page === "login" ? "page" : undefined}>
              {t("signIn")}
            </Link>
            <Link href={`/auth/signup${query}`} aria-current={page === "signup" ? "page" : undefined}>
              {t("signUp")}
            </Link>
          </div>
          <div className="a-auth-body">
          <h1 id="auth-title">{page === "signup" ? t("createTitle") : t("welcomeBack")}</h1>
          <form action={action} className="a-auth-form">
            <input type="hidden" name="next" value={next} />
            {page === "signup" ? (
              <>
                <fieldset className="a-field" style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend style={{ marginBottom: 8 }}>{t("forWho")}</legend>
                  <div className="a-choice-grid">
                    <label className="a-choice">
                      <input
                        type="radio"
                        name="workspace"
                        value="individual"
                        checked={!team}
                        onChange={() => setWorkspace("individual")}
                      />
                      <span className="a-choice-icon">
                        <UserRound size={18} aria-hidden />
                      </span>
                      <strong>{t("forMe")}</strong>
                      <span>{t("forMeBody")}</span>
                    </label>
                    <label className="a-choice">
                      <input
                        type="radio"
                        name="workspace"
                        value="organisation"
                        checked={team}
                        onChange={() => setWorkspace("organisation")}
                      />
                      <span className="a-choice-icon">
                        <Building2 size={18} aria-hidden />
                      </span>
                      <strong>{t("forTeam")}</strong>
                      <span>{t("forTeamBody")}</span>
                    </label>
                  </div>
                </fieldset>
                <div className="a-auth-pair">
                <label className="a-field">
                  {t("name")}
                  <input className="a-input" name="display_name" required minLength={2} maxLength={80} autoComplete="name" defaultValue={values.display_name} />
                </label>
                <label className="a-field">
                  {t("email")}
                  <input className="a-input" type="email" name="email" required autoComplete="email" defaultValue={values.email} />
                </label>
                </div>
              </>
            ) : (
              <label className="a-field">
                {t("email")}
                <input className="a-input" type="email" name="email" required autoComplete="email" defaultValue={values.email} />
              </label>
            )}
            <label className="a-field">
              {t("password")}
              <input
                className="a-input"
                type="password"
                name="password"
                required
                minLength={page === "signup" ? 8 : 1}
                autoComplete={page === "signup" ? "new-password" : "current-password"}
              />
              {page === "signup" ? <small>{t("passwordHint")}</small> : null}
            </label>
            {page === "signup" && team ? (
              <>
                <div className="a-auth-pair">
                  <label className="a-field">
                    {t("orgName")}
                    <input className="a-input" name="org_name" required minLength={2} maxLength={120} defaultValue={values.org_name} />
                  </label>
                  <label className="a-field">
                    {t("orgType")}
                    <select className="a-select" name="org_type" defaultValue={values.org_type ?? "company"}>
                      <option value="company">{t("company")}</option>
                      <option value="institution">{t("institution")}</option>
                    </select>
                  </label>
                </div>
                <div className="a-auth-pair is-wide-first">
                  <label className="a-field">
                    {t("industry")}
                    <input className="a-input" name="industry" maxLength={120} defaultValue={values.industry} />
                  </label>
                  <label className="a-field">
                    {t("size")}
                    <input className="a-input" type="number" min={0} name="size" defaultValue={values.size ?? "10"} />
                  </label>
                </div>
              </>
            ) : null}
            {page === "signup" && !team ? (
              <label className="a-field">
                {t("joinCode")}
                <input className="a-input" name="join_code" maxLength={16} autoCapitalize="characters" defaultValue={values.join_code ?? params.get("code") ?? ""} />
                <small>{t("joinCodeHint")}</small>
              </label>
            ) : null}
            {page === "signup" ? (
              <label className="a-check">
                <input type="checkbox" name="consent" required defaultChecked={values.consent === "on"} />
                {t("consent")}
              </label>
            ) : null}
            {state.error ? (
              <p className="a-notice" data-tone="error" role="alert">
                {state.error}
              </p>
            ) : null}
            <button className="a-btn is-block" type="submit" disabled={pending}>
              {pending ? t("working") : page === "signup" ? t("signUp") : t("signIn")}
            </button>
          </form>
          <p className="a-small a-muted" style={{ margin: 0, textAlign: "center" }}>
            {page === "signup" ? t("haveAccount") : t("noAccount")}{" "}
            <Link className="a-link" href={`/auth/${page === "signup" ? "login" : "signup"}${query}`}>
              {page === "signup" ? t("signIn") : t("signUp")}
            </Link>
          </p>
          </div>
        </section>
        {/* The landing page's drawings: a career path for individuals, an office for teams. */}
        <section className="a-auth-art" aria-hidden="true">
          <div className="a-auth-art-copy">
            <h2>{team ? t("artTeamTitle") : t("artTitle")}</h2>
            <p>{team ? t("artTeamBody") : t("artBody")}</p>
          </div>
          <div className="a-auth-art-fig">{team ? <OrgScene /> : <PathScene />}</div>
        </section>
      </div>
    </main>
  );
}
