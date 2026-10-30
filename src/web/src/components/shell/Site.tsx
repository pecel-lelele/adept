import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { getAccount } from "@/lib/auth/account";

import { LocaleSwitcher } from "../LocaleSwitcher";
import { BrandLogo } from "./Brand";
import { SiteMenu } from "./SiteMenu";

/**
 * Public header (partner design), pinned while scrolling: logo, section links, the audience
 * switch (landing only) and language pill, then sign-in and a green "Create account".
 * Signed-in visitors get a link to their workspace. Phones get a hamburger menu instead.
 */
export async function SiteHeader({
  signup,
  audienceSwitch,
}: {
  signup?: ReactNode;
  audienceSwitch?: ReactNode;
}) {
  const t = await getTranslations("ui");
  const account = await getAccount();
  const home = account ? (account.kind === "org_admin" ? "/org" : "/app") : null;
  const links = (
    <>
      <Link href="/#features">{t("landing.navFeatures")}</Link>
      <Link href="/#how">{t("landing.navHow")}</Link>
      <Link href="/#faq">{t("landing.navFaq")}</Link>
      <Link href="/about">{t("landing.navAbout")}</Link>
    </>
  );
  const homeLink = home ? (
    <Link className="a-btn is-small" href={home}>
      {t("nav.home")} <ArrowUpRight size={15} aria-hidden />
    </Link>
  ) : null;
  return (
    <header className="a-site-head">
      <div className="a-wrap a-site-head-in">
        <BrandLogo href="/" />
        <nav className="a-site-nav" aria-label={t("landing.navHow")}>
          {links}
        </nav>
        <div className="a-site-actions">
          {audienceSwitch ?? null}
          <span className="a-site-wide">
            <LocaleSwitcher />
          </span>
          {homeLink ?? (
            <span className="a-site-wide a-site-auth">
              <Link className="a-site-login" href="/auth/login">
                {t("auth.signIn")}
              </Link>
              {signup ?? (
                <Link className="a-btn is-small" href="/auth/signup">
                  {t("auth.signUp")} <ArrowUpRight size={15} aria-hidden />
                </Link>
              )}
            </span>
          )}
          <SiteMenu>
            <nav className="a-menu-links" aria-label={t("landing.navHow")}>
              {links}
            </nav>
            <LocaleSwitcher />
            <div className="a-menu-auth">
              {homeLink ?? (
                <>
                  <Link className="a-btn is-ghost is-block" href="/auth/login">
                    {t("auth.signIn")}
                  </Link>
                  {signup ?? (
                    <Link className="a-btn is-block" href="/auth/signup">
                      {t("auth.signUp")}
                    </Link>
                  )}
                </>
              )}
            </div>
          </SiteMenu>
        </div>
      </div>
    </header>
  );
}

/** Public footer (partner design): tagline, three link columns, legal line, a large closing word. */
export async function SiteFooter({ note }: { note?: ReactNode }) {
  const t = await getTranslations("ui.landing");
  const tn = await getTranslations("ui.nav");
  const privacy = await getTranslations("privacy");
  return (
    <footer className="a-site-foot">
      <div className="a-wrap">
        <div className="a-site-foot-top">
          <div>
            <BrandLogo href="/" />
            <p>{t("footTag")}</p>
          </div>
          <div>
            <b>{t("footPlatform")}</b>
            <Link href="/">{t("footForMe")}</Link>
            <Link href="/?for=teams">{t("footForTeam")}</Link>
            <Link href="/#how">{t("navHow")}</Link>
          </div>
          <div>
            <b>{t("footExplore")}</b>
            <Link href="/#start">{t("ctaUpload")}</Link>
            <Link href="/app/radar">{tn("radar")}</Link>
            <Link href="/#faq">{t("navFaq")}</Link>
          </div>
          <div>
            <b>{t("footTrust")}</b>
            <Link href="/about">
              {t("footMethods")} <ArrowUpRight size={13} aria-hidden />
            </Link>
            <span>{t("footHuman")}</span>
            <Link href="/privacy">{privacy("footerLink")}</Link>
            <span>{t("footPlace")}</span>
          </div>
        </div>
        <div className="a-site-foot-bottom">
          <span>{t("footCopy")}</span>
          {note ?? null}
        </div>
        <div className="a-site-foot-word" aria-hidden>
          {t("footWord")}
        </div>
      </div>
    </footer>
  );
}
