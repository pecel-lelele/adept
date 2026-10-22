import { LogOut } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense, type ReactNode } from "react";

import type { Workspace } from "@/config/navigation";
import type { Account } from "@/lib/auth/account";

import { LocaleSwitcher } from "../LocaleSwitcher";
import { ScenarioToggle } from "../ScenarioToggle";
import { BrandMark } from "./Brand";
import { ScenarioSlot, SideNav, TabBar, TopTitle } from "./Nav";

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "A"
  );
}

/**
 * One shell for every workspace. Desktop: sidebar (grouped, journey steps numbered) and a
 * top bar with the page title and, where it matters, the AI-scenario switch. Mobile: compact
 * top bar and a fixed bottom tab bar whose "More" sheet holds the rest.
 */
export async function Shell({
  ws,
  account,
  orgName,
  doneSteps = [],
  children,
}: {
  ws: Workspace;
  account: Account | null;
  orgName?: string;
  doneSteps?: number[];
  children: ReactNode;
}) {
  const t = await getTranslations("ui");
  const name = account?.display_name ?? "Adept";
  return (
    <div className="a-shell" data-mode={ws.mode}>
      <a className="a-skip" href="#a-main">
        {t("nav.skip")}
      </a>
      <aside className="a-side">
        <Link href={ws.home} className="a-brand">
          <BrandMark />
          adept
        </Link>
        <Suspense>
          <SideNav ws={ws} doneSteps={doneSteps} />
        </Suspense>
        <div className="a-side-foot">
          <div className="a-account">
            <span className="a-avatar" aria-hidden>
              {initials(name)}
            </span>
            <span style={{ minWidth: 0 }}>
              <strong>{name}</strong>
              <small>{orgName ?? t(ws.mode === "organisation" ? "nav.organisation" : "nav.learner")}</small>
            </span>
          </div>
          <div className="a-side-actions">
            <LocaleSwitcher />
            <a href="/auth/logout">
              <LogOut size={14} aria-hidden /> {t("nav.signOut")}
            </a>
          </div>
        </div>
      </aside>
      <div className="a-col">
        <header className="a-top">
          <Link href={ws.home} className="a-top-brand">
            <BrandMark />
            adept
          </Link>
          <Suspense>
            <TopTitle ws={ws} />
          </Suspense>
          <div className="a-top-tools">
            <Suspense>
              <ScenarioSlot ws={ws}>
                <ScenarioToggle />
              </ScenarioSlot>
            </Suspense>
            <Link href="/about" className="a-link a-small a-hide-mobile">
              {t("nav.about")}
            </Link>
          </div>
        </header>
        <main id="a-main" className="a-main">
          {children}
        </main>
        <footer className="a-foot">{t("shell.disclaimer")}</footer>
      </div>
      <Suspense>
        <TabBar ws={ws} tools={<LocaleSwitcher />} />
      </Suspense>
    </div>
  );
}
