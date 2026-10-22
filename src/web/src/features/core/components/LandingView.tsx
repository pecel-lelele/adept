import { Compass, Grid3x3, Layers, Radar, Route, Ticket, UserRoundCheck, Users } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { BrandMark } from "@/components/shell/Brand";
import { RiseArt } from "@/components/viz/RiseArt";
import { Scene3D } from "@/components/viz/Scene3D";
import { call, getApi } from "@/lib/api";
import { getAccount } from "@/lib/auth/account";

import { AudienceRoot, AudienceToggle, type Audience } from "./AudienceSwitch";
import { CvPreview } from "./CvPreview";

/**
 * Public home with a "For me ⇄ For my team" switch. For me: upload a CV and see part of the
 * result at once; the rest unlocks with a free account. For my team: what a manager gets and
 * one call to action. Both views render on the server; the switch only re-themes and swaps.
 */
export async function LandingView({ audience }: { audience: Audience }) {
  const t = await getTranslations("ui.landing");
  const ta = await getTranslations("ui.auth");
  const tn = await getTranslations("ui.nav");
  const tc = await getTranslations("common");
  const [account, freshness] = await Promise.all([
    getAccount(),
    getApi().then((api) => call(api.GET("/api/v1/meta/data-freshness"))),
  ]);
  const home = account ? (account.kind === "org_admin" ? "/org" : "/app") : null;
  const date = freshness.ok ? freshness.data.snapshot_date : null;
  const meSteps = [
    { icon: Layers, title: t("step1"), body: t("step1Body") },
    { icon: Radar, title: t("step2"), body: t("step2Body") },
    { icon: Compass, title: t("step3"), body: t("step3Body") },
    { icon: Route, title: t("step4"), body: t("step4Body") },
  ];
  const teamSteps = [
    { icon: Ticket, title: t("tStep1"), body: t("tStep1Body") },
    { icon: UserRoundCheck, title: t("tStep2"), body: t("tStep2Body") },
    { icon: Grid3x3, title: t("tStep3"), body: t("tStep3Body") },
    { icon: Users, title: t("tStep4"), body: t("tStep4Body") },
  ];
  const steps = (list: typeof meSteps) => (
    <ol className="a-land-steps">
      {list.map((s, i) => (
        <li className="a-land-step" key={s.title}>
          <span className="a-land-step-icon">
            <s.icon size={20} strokeWidth={1.7} aria-hidden />
          </span>
          <span className="a-muted a-small">0{i + 1}</span>
          <h3>{s.title}</h3>
          <p>{s.body}</p>
        </li>
      ))}
    </ol>
  );

  return (
    <AudienceRoot initial={audience}>
      <header className="a-page-top">
        <Link href="/" className="a-brand" style={{ padding: 0 }}>
          <BrandMark />
          adept
        </Link>
        <nav>
          <Link href="/about" className="a-link a-hide-mobile">
            {tn("about")}
          </Link>
          <span className="a-hide-mobile">
            <LocaleSwitcher />
          </span>
          {home ? (
            <Link className="a-btn is-small" href={home}>
              {tn("home")}
            </Link>
          ) : (
            <>
              <Link className="a-btn is-small is-ghost" href="/auth/login">
                {ta("signIn")}
              </Link>
              <Link className="a-btn is-small a-hide-mobile a-for-me" href="/auth/signup">
                {ta("signUp")}
              </Link>
              <Link className="a-btn is-small a-hide-mobile a-for-team" href="/auth/signup?mode=organisation">
                {ta("signUp")}
              </Link>
            </>
          )}
        </nav>
      </header>

      <div className="a-land">
        <div className="a-switch-wrap">
          <AudienceToggle />
        </div>

        {/* ---- for me ---- */}
        <div className="a-for-me">
          <section className="a-land-hero">
            <div>
              {date ? (
                <span className="a-pill-badge">
                  <b>AI</b> {t("badge", { date })}
                </span>
              ) : null}
              <h1 className="a-display">
                <span>{t("line1")}</span>
                <span className="is-muted">{t("line2")}</span>
                <span className="a-highlight">{t("highlight")}</span>
              </h1>
              <p className="a-lead">{t("sub")}</p>
            </div>
            <RiseArt />
          </section>
          <CvPreview />
          <section aria-labelledby="how-me" style={{ marginTop: 56 }}>
            <h2 id="how-me" className="a-section-title">
              {t("howTitle")}
            </h2>
            {steps(meSteps)}
          </section>
        </div>

        {/* ---- for my team ---- */}
        <div className="a-for-team">
          <section className="a-land-hero">
            <div>
              <h1 className="a-display">
                <span>{t("tLine1")}</span>
                <span className="is-muted">{t("tLine2")}</span>
                <span className="a-highlight">{t("tHighlight")}</span>
              </h1>
              <p className="a-lead">{t("tSub")}</p>
              <div className="a-hero-actions" style={{ marginTop: 24 }}>
                <Link className="a-btn" href={home ?? "/auth/signup?mode=organisation"}>
                  {t("tCta")}
                </Link>
                <Link className="a-btn is-ghost" href="/auth/login?mode=organisation">
                  {t("tSignIn")}
                </Link>
              </div>
            </div>
            <Scene3D variant="grid" />
          </section>
          <section aria-labelledby="how-team" style={{ marginTop: 40 }}>
            <h2 id="how-team" className="a-section-title">
              {t("tHowTitle")}
            </h2>
            {steps(teamSteps)}
            <p className="a-muted a-small" style={{ marginTop: 20 }}>
              {t("tPrivacy")}
            </p>
          </section>
        </div>

        <footer className="a-land-foot">
          <span>{tc("humanInCharge")}</span>
          <LocaleSwitcher />
          {freshness.ok ? (
            <span>
              {t("estimate", { date: freshness.data.snapshot_date })} ·{" "}
              {freshness.data.sources.map((s) => s.name).join(", ")}
            </span>
          ) : null}
        </footer>
      </div>
    </AudienceRoot>
  );
}
