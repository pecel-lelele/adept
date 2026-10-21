import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense, type ReactNode } from "react";
import type { NavItem } from "@/config/navigation";
import {
  WorkspaceNavigation,
  JourneyControls,
} from "@/features/core/components/WorkspaceNavigation";
import { LocaleSwitcher } from "../LocaleSwitcher";
import { ScenarioToggle } from "../ScenarioToggle";
export async function Shell({
  nav,
  modeLabel,
  showScenario = true,
  children,
}: {
  nav: readonly NavItem[];
  modeLabel: string;
  showScenario?: boolean;
  children: ReactNode;
}) {
  const t = await getTranslations("common");
  const org = nav.some((item) => item.href === "/org");
  return (
    <div className={`workspace ${org ? "workspace-org" : "workspace-learner"}`}>
      <a className="skip-link" href="#workspace-main">
        {t("workspace.skip")}
      </a>
      <aside className="workspace-sidebar">
        <Link href="/" className="workspace-brand">
          <span aria-hidden>ɑ</span> adept<span className="brand-dot">.</span>
        </Link>
        <p className="workspace-eyebrow">
          {modeLabel} / {t("workspace.workspace")}
        </p>
        <Suspense>
          <WorkspaceNavigation nav={nav} />
        </Suspense>
        <div className="workspace-help">
          <span className="workspace-eyebrow">{t("workspace.human")}</span>
          <p>{t("humanInCharge")}</p>
          <Link href="/about">{t("nav.about")} ↗</Link>
        </div>
        <Link href="/journey" className="workspace-map">
          {t("workspace.map")} ↗
        </Link>
      </aside>
      <div className="workspace-body">
        <header className="workspace-topbar">
          <span className="workspace-status">
            <span /> {t("workspace.demo")}
          </span>
          <div className="workspace-tools">
            {showScenario ? (
              <Suspense>
                <ScenarioToggle />
              </Suspense>
            ) : null}
            <LocaleSwitcher />
          </div>
          <a href="/auth/logout" className="workspace-exit">
            {t("workspace.exit")}
          </a>
        </header>
        <main id="workspace-main" className="workspace-main">
          <Suspense>
            <JourneyControls />
          </Suspense>
          {children}
        </main>
        <footer className="workspace-footer">
          {t("workspace.disclaimer")}
        </footer>
      </div>
    </div>
  );
}
