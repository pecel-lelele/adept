"use client";

import { ArrowLeft, Building2, LineChart, Lock, ShieldCheck, UserRound, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useActionState, useState } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { BrandMark } from "@/components/shell/Brand";
import { FeatureArt } from "@/components/viz/FeatureArt";
import { OrgScene } from "@/components/viz/OrgScene";
import { PathScene } from "@/components/viz/PathScene";

import { loginAction, signupAction, type AuthState } from "../auth-actions";

type Page = "login" | "signup";

/** Real sign-up and sign-in. Every account and organisation is stored in PostgreSQL. */
export function AuthView() {
  const t = useTranslations("ui.auth");
  const te = useTranslations("ui.apiErrors");
  const params = useSearchParams();
  const next = params.get("next") ?? "";
  // Rendered by the shared (entry) layout, so it stays mounted between /auth/login and
  // /auth/signup: the route only picks the tab; the pill slides and the form cross-fades.
  const page: Page = usePathname().endsWith("/signup") ? "signup" : "login";
  const tabHref = (p: Page) => `/auth/${p}${params.toString() ? `?${params.toString()}` : ""}`;
  // When the user arrives from the "Join an organisation" page via the team-account link,
  // role=team locks the signup form to "For my team" and hides the individual option.
  const roleTeam = page === "signup" && params.get("role") === "team";
  const [state, action, pending] = useActionState<AuthState, FormData>(
    (prev, form) => (form.get("_page") === "signup" ? signupAction(prev, form) : loginAction(prev, form)),
    {},
  );
  const values = state.values ?? {};
  // The panel stays mounted across tabs, so a "For my team" choice must not leak into Sign in:
  // each tab starts from the link that opened it (?mode=), exactly like arriving from the
  // landing page. A choice made on Create account lasts only while that tab is open.
  type Workspace = "individual" | "organisation";
  const fromUrl: Workspace = (params.get("mode") === "organisation" || roleTeam) ? "organisation" : "individual";
  const [choice, setChoice] = useState<Workspace | null>(null);
  const [choicePage, setChoicePage] = useState<Page>(page);
  if (choicePage !== page) {
    setChoicePage(page);
    setChoice(null);
  }
  const setWorkspace = (w: Workspace) => setChoice(w);
  const workspace: Workspace =
    page === "signup"
      ? (choice ?? (values._page === "signup" && values.workspace === "organisation" ? "organisation" : fromUrl))
      : fromUrl;
  const team = workspace === "organisation";

  return (
    <main className="a-page a-authpage" data-mode={team ? "organisation" : "individual"} data-role-team={roleTeam || undefined}>
      {/* Soft moving colour behind the panel, so the page never reads as empty white. */}
      <div className="a-auth-bg" aria-hidden="true">
        <span className="a-auth-blob is-1" />
        <span className="a-auth-blob is-2" />
        <span className="a-auth-blob is-3" />
        <span className="a-auth-grid" />
      </div>
      <header className="a-page-top">
        {/* Static brand — not a link, so clicking it here never navigates away or clears the session. */}
        <span className="a-brand" aria-label="Adept">
          <BrandMark />
          <span>adept<span className="a-brand-dot">.</span></span>
        </span>
      </header>
      <div className="a-auth">
        <section className="a-auth-card" aria-labelledby="auth-title" data-page={page}>
          {/* Back arrow + tab switcher share one grid row so the card layout isn't disrupted.
              A full navigation refreshes the landing page with the current session cookie. */}
          <div>
            <Link
              href="/"
              prefetch={false}
              className="a-auth-back"
              aria-label={t("backHome")}
              onNavigate={(event) => {
                event.preventDefault();
                window.location.assign(new URL("/", window.location.origin).href);
              }}
            >
              <ArrowLeft size={16} aria-hidden />
              <span>{t("back")}</span>
            </Link>
            <div className="a-tabswitch" role="tablist" data-active={page}>
              {(["login", "signup"] as const).map((p) => (
                <Link key={p} href={tabHref(p)} replace scroll={false} role="tab" aria-selected={page === p}>
                  {p === "login" ? t("signIn") : t("signUp")}
                </Link>
              ))}
            </div>
          </div>
          <div className="a-auth-body" key={page}>
          {/* Show title only on Sign in — signup form is compact enough without it.
              A visually-hidden heading is kept on signup so aria-labelledby="auth-title"
              always resolves to an accessible name for screen readers. */}
          {page === "login" ? (
            <div className="a-auth-head">
              <h1 id="auth-title">{t("welcomeBack")}</h1>
              <p>{t(team ? "signInTeamSub" : "signInSub")}</p>
            </div>
          ) : (
            <h1 id="auth-title" className="sr-only">{t("createTitle")}</h1>
          )}
          <form action={action} className="a-auth-form">
            <input type="hidden" name="next" value={next} />
            <input type="hidden" name="_page" value={page} />
            {page === "signup" ? (
              <>
                <fieldset className="a-field" style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend style={{ marginBottom: 8 }}>{t("forWho")}</legend>
                  <div className="a-choice-grid">
                    {!roleTeam ? (
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
                    ) : null}
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
            {page === "signup" ? (
              <>
                {/* Both variants share one slot sized to the taller one, so the panel keeps its
                    size; the inactive one fades out and its fieldset is disabled (not validated,
                    not submitted). */}
                <div className="a-variant">
                <fieldset className="a-variant-pane" data-open={team} disabled={!team} aria-hidden={!team}>
                  <div className="a-variant-in">
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
                  </div>
                </fieldset>
                <fieldset className="a-variant-pane" data-open={!team} disabled={team} aria-hidden={team}>
                  <div className="a-variant-in">
                    <label className="a-field">
                      {t("joinCode")}
                      <input className="a-input" name="join_code" maxLength={16} autoCapitalize="characters" defaultValue={values.join_code ?? params.get("code") ?? ""} />
                      <small>{t("joinCodeHint")}</small>
                    </label>
                    <label className="a-check" style={{ marginTop: "0.5rem" }}>
                      <input type="checkbox" name="share_skills" defaultChecked={values.share_skills === "on"} />
                      <span>{t("shareSkills")}</span>
                    </label>
                    <small className="a-muted" style={{ display: "block", marginTop: "0.25rem" }}>
                      {t("shareSkillsHint")}
                    </small>
                  </div>
                </fieldset>
                </div>
              </>
            ) : null}
            {page === "signup" ? (
              <label className="a-check">
                <input type="checkbox" name="consent" required defaultChecked={values.consent === "on"} />
                {t("consent")}
              </label>
            ) : null}
            {page === "signup" ? (
              <p className="a-small a-muted" style={{ margin: 0 }}>
                <Link className="a-link" href="/privacy">
                  {t("privacyLink")}
                </Link>
              </p>
            ) : null}
            {state.error && (state.values?._page ?? page) === page ? (
              <p className="a-notice" data-tone="error" role="alert">
                {errorMessage(te, state.error)}
              </p>
            ) : null}
            <button className="a-btn is-block" type="submit" disabled={pending} aria-busy={pending}>
              {pending ? t("working") : page === "signup" ? t("signUp") : t("signIn")}
            </button>
          </form>
          <p className="a-small a-muted" style={{ margin: 0, textAlign: "center" }}>
            {page === "signup" ? t("haveAccount") : t("noAccount")}{" "}
            <Link className="a-link" href={tabHref(page === "signup" ? "login" : "signup")} replace scroll={false}>
              {page === "signup" ? t("signIn") : t("signUp")}
            </Link>
          </p>
          </div>
          <ul className="a-auth-trust">
            <li>
              <Lock size={15} aria-hidden /> {t("trustCv")}
            </li>
            <li>
              <ShieldCheck size={15} aria-hidden /> {t("trustSources")}
            </li>
            <li>
              <UserRound size={15} aria-hidden /> {t("trustYou")}
            </li>
          </ul>
        </section>
        {/* The landing page's drawings: a career path for individuals, an office for teams. */}
        {/* Sign in: what is waiting for you (skills radar, or the team roster). Create account:
            where you are going (career path, or the office on the forest background). */}
        <section className="a-auth-art" aria-hidden="true" data-tone={team ? "forest" : "emerald"}>
          <span className="a-auth-art-glow" />
          <div className="a-auth-art-copy" key={`copy-${page}-${workspace}`}>
            <span className="a-auth-art-eyebrow">
              {team ? <Users size={14} aria-hidden /> : <LineChart size={14} aria-hidden />}
              {t(team ? "eyebrowTeam" : "eyebrowMe")}
            </span>
            <h2>
              {page === "login"
                ? t(team ? "signInTeamArtTitle" : "signInArtTitle")
                : t(team ? "artTeamTitle" : "artTitle")}
            </h2>
            <p>
              {page === "login"
                ? t(team ? "signInTeamArtBody" : "signInArtBody")
                : t(team ? "artTeamBody" : "artBody")}
            </p>
          </div>
          <div className="a-auth-art-fig" key={`fig-${page}-${workspace}`}>
            <div className="a-auth-glass">
              {page === "login" ? (
                <FeatureArt variant={team ? "roster" : "radar"} className="is-auth" />
              ) : team ? (
                <OrgScene />
              ) : (
                <PathScene />
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
