import { BookOpen, Building2, LogOut } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense, type ReactNode } from "react";

import type { Workspace } from "@/config/navigation";
import type { Account } from "@/lib/auth/account";
import { PERSONAL } from "@/lib/auth/workspace";
import type { WorkspaceOption } from "@/lib/auth/workspaces";

import { AdiAssistant } from "../adi/AdiAssistant";
import { LocaleSwitcher } from "../LocaleSwitcher";
import { ScenarioToggle } from "../ScenarioToggle";
import { BrandLogo } from "./Brand";
import { NavProgress, PageEnter } from "./Motion";
import { ScenarioSlot, SideNav, TabBar } from "./Nav";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

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
 * One shell for every workspace, styled after the partner design (frontend/adept). Desktop:
 * a sidebar only (journey steps numbered, the rest in a collapsible "More", then the
 * account) and no bar above the content. On pages that depend on it, the "AI pace" switch
 * sits at the top right of the page. Phones: a fixed bottom tab bar replaces the sidebar.
 */
export async function Shell({
  ws,
  account,
  orgName,
  doneSteps = [],
  workspaces = [],
  current = PERSONAL,
  children,
}: {
  ws: Workspace;
  account: Account | null;
  orgName?: string;
  doneSteps?: number[];
  /** Workspaces this account can switch to, and the one shown. */
  workspaces?: WorkspaceOption[];
  current?: string;
  children: ReactNode;
}) {
  const t = await getTranslations("ui");
  const name = account?.display_name ?? "Adept";
  // People in no organisation always see how to join one (sidebar and mobile menu).
  const joinable = ws.mode === "individual" && !!account && !workspaces.some((w) => w.kind === "org");
  const space =
    ws.mode === "organisation" || ws.mode === "employee" ? "nav.organisation" : ws.mode === "admin" ? "nav.admin" : "nav.learner";
  const switcher = <WorkspaceSwitcher workspaces={workspaces} current={current} />;
  return (
    <div className="a-shell" data-mode={ws.mode}>
      <Suspense>
        <NavProgress />
      </Suspense>
      <a className="a-skip" href="#a-main">
        {t("nav.skip")}
      </a>
      <aside className="a-side">
        <BrandLogo href="/" />
        <span className="a-eyebrow a-side-space">{t(space)}</span>
        {switcher}
        <Suspense>
          <SideNav ws={ws} doneSteps={doneSteps} />
        </Suspense>
        <div className="a-side-foot">
          {joinable ? (
            <Link href="/app/join" className="a-side-join">
              <Building2 size={16} strokeWidth={1.8} aria-hidden />
              <span>
                <strong>{t("page.joinTeam")}</strong>
                <small>{t("page.joinTeamHint")}</small>
              </span>
            </Link>
          ) : null}
          <Link href="/about" className="a-side-about">
            <BookOpen size={16} strokeWidth={1.7} aria-hidden /> {t("nav.about")}
          </Link>
          <div className="a-account">
            <span className="a-status-dot" aria-hidden />
            <span className="a-avatar" aria-hidden>
              {initials(name)}
            </span>
            <span style={{ minWidth: 0 }}>
              <strong>{name}</strong>
              <small>{orgName ?? t(space)}</small>
            </span>
            <a className="a-iconlink" href="/auth/logout" title={t("nav.signOut")} aria-label={t("nav.signOut")}>
              <LogOut size={15} aria-hidden />
            </a>
          </div>
          <LocaleSwitcher />
        </div>
      </aside>
      <div className="a-col">
        <Suspense>
          <ScenarioSlot ws={ws}>
            <div className="a-pagebar">
              <ScenarioToggle />
            </div>
          </ScenarioSlot>
        </Suspense>
        <main id="a-main" className="a-main">
          <PageEnter>{children}</PageEnter>
        </main>
        <footer className="a-foot">{t("shell.disclaimer")}</footer>
      </div>
      <Suspense>
        <TabBar
          ws={ws}
          tools={
            <>
              <WorkspaceSwitcher workspaces={workspaces} current={current} presentation="list" />
              <LocaleSwitcher />
              {joinable ? (
                <Link href="/app/join" className="a-link">
                  <Building2 size={16} aria-hidden /> {t("page.joinTeam")}
                </Link>
              ) : null}
            </>
          }
        />
      </Suspense>
      {account && ws.mode !== "admin" ? (
        <Suspense>
          <AdiAssistant who={account.id} workspace={current} workspaceName={current === PERSONAL ? "" : (orgName ?? "")} />
        </Suspense>
      ) : null}
    </div>
  );
}
