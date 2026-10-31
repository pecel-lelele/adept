"use client";

import {
  BookOpen,
  BriefcaseBusiness,
  Check,
  ChartNoAxesCombined,
  ClipboardCheck,
  Compass,
  Database,
  Grid3x3,
  House,
  Layers,
  Leaf,
  LogOut,
  LockKeyhole,
  Menu,
  Radar,
  Route,
  Settings2,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import {
  activeItem,
  allItems,
  type IconName,
  type NavItem,
  type Workspace,
} from "@/config/navigation";
import { journeyHref } from "@/lib/navigation";

const ICONS: Record<IconName, LucideIcon> = {
  home: House,
  skills: Layers,
  radar: Radar,
  roles: Compass,
  plan: Route,
  progress: Target,
  courses: BookOpen,
  impact: Leaf,
  team: Users,
  gaps: Grid3x3,
  verify: ClipboardCheck,
  settings: Settings2,
  sources: Database,
  snapshots: ChartNoAxesCombined,
  jobs: BriefcaseBusiness,
};

function useHref() {
  const params = useSearchParams();
  const path = usePathname();
  return (href: string) => journeyHref(href, params, path);
}

function isCurrent(ws: Workspace, item: NavItem, pathname: string): boolean {
  return activeItem(ws, pathname)?.href === item.href;
}

/** Desktop sidebar: every page always visible, in labelled groups (journey first). */
export function SideNav({ ws, doneSteps, roleChosen = true }: { ws: Workspace; doneSteps: number[]; roleChosen?: boolean }) {
  const t = useTranslations("ui.nav");
  const pathname = usePathname();
  const href = useHref();

  const link = (item: NavItem) => {
    const Icon = ICONS[item.icon];
    const done = item.step ? doneSteps.includes(item.step) : false;
    const locked = ws.mode === "individual" && !roleChosen && (item.key === "plan" || item.key === "progress");
    return (
      <Link
        key={item.href}
        href={href(locked ? "/app/matches?choose_role=1" : item.href)}
        className="a-navlink"
        aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
        title={locked ? t("chooseRoleFirst") : undefined}
        aria-label={locked ? `${t(item.key)} · ${t("chooseRoleFirst")}` : undefined}
        data-locked={locked || undefined}
      >
        <Icon size={18} strokeWidth={1.8} aria-hidden />
        <span className="a-navlink-text">{t(item.key)}</span>
        {locked ? <LockKeyhole size={14} aria-hidden /> : null}
        {item.step ? (
          <span className="a-step" data-done={done} title={t("journey")}>
            {done ? <Check size={11} strokeWidth={3} aria-hidden /> : item.step}
          </span>
        ) : null}
      </Link>
    );
  };

  return (
    <nav aria-label={t(ws.mode === "organisation" || ws.mode === "employee" ? "organisation" : "learner")} className="a-sidenav">
      {ws.groups.map((group, i) => (
        <div className="a-navgroup" key={group.label}>
          {ws.groups.length > 1 ? (
            <span className="a-navgroup-label" id={`nav-${i}`}>
              {t(group.label)}
            </span>
          ) : null}
          {group.items.map(link)}
        </div>
      ))}
    </nav>
  );
}

/** Shows its children (the scenario switch) only on pages where scenarios matter. */
export function ScenarioSlot({ ws, children }: { ws: Workspace; children: ReactNode }) {
  const pathname = usePathname();
  return activeItem(ws, pathname)?.scenario ? <>{children}</> : null;
}

/**
 * Mobile: a fixed bottom bar with four destinations + "More". "More" opens a bottom sheet
 * with every other page as a grid of large targets, so nothing scrolls sideways.
 */
export function TabBar({ ws, tools, roleChosen = true }: { ws: Workspace; tools: ReactNode; roleChosen?: boolean }) {
  const t = useTranslations("ui.nav");
  const pathname = usePathname();
  const href = useHref();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  // The sheet belongs to the page it was opened on; navigating closes it.
  const open = openedAt === pathname;
  const sheetRef = useRef<HTMLDivElement>(null);
  const moreRef = useRef<HTMLButtonElement>(null);
  // Dismissing the sheet (Escape, backdrop, Close) hands focus back to "More".
  const dismiss = useCallback(() => {
    setOpenedAt(null);
    moreRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const sheet = sheetRef.current;
    const focusables = () =>
      Array.from(sheet?.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), summary, select, input") ?? [])
        .filter((element) => element.getClientRects().length > 0);
    focusables()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        dismiss();
        return;
      }
      if (e.key !== "Tab") return;
      // Keep keyboard focus inside the modal sheet.
      const list = focusables();
      const first = list[0];
      const last = list[list.length - 1];
      if (!first || !last) return;
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !sheet?.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !sheet?.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, dismiss]);

  const items = allItems(ws);
  const tabs = ws.tabs
    .map((key) => items.find((i) => i.key === key))
    .filter((i): i is NavItem => Boolean(i));
  const rest = items.filter((i) => !tabs.includes(i));
  const restActive = rest.some((i) => isCurrent(ws, i, pathname));
  const locked = (item: NavItem) => ws.mode === "individual" && !roleChosen && (item.key === "plan" || item.key === "progress");

  return (
    <>
      <nav className="a-tabs" aria-label={t("journey")}>
        {tabs.map((item) => {
          const Icon = ICONS[item.icon];
          return (
            <Link
              key={item.href}
              href={href(locked(item) ? "/app/matches?choose_role=1" : item.href)}
              className="a-tab"
              aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
              title={locked(item) ? t("chooseRoleFirst") : undefined}
              aria-label={locked(item) ? `${t(item.key)} · ${t("chooseRoleFirst")}` : undefined}
              data-locked={locked(item) || undefined}
            >
              <span className="a-tab-icon">
                <Icon size={20} strokeWidth={1.8} aria-hidden />
                {locked(item) ? <LockKeyhole className="a-nav-lock" size={12} aria-hidden /> : null}
              </span>
              <span>{t(item.key)}</span>
            </Link>
          );
        })}
        <button
          ref={moreRef}
          type="button"
          className="a-tab"
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-current={restActive ? "page" : undefined}
          onClick={() => setOpenedAt(pathname)}
        >
          <span className="a-tab-icon">
            <Menu size={20} strokeWidth={1.8} aria-hidden />
          </span>
          <span>{t("more")}</span>
        </button>
      </nav>
      {open ? (
        <>
          <div className="a-sheet-backdrop" onClick={dismiss} />
          <div ref={sheetRef} className="a-sheet" role="dialog" aria-modal="true" aria-label={t("more")}>
            <div className="a-sheet-grip" />
            <div className="a-sheet-grid">
              {rest.map((item) => {
                const Icon = ICONS[item.icon];
                return (
                  <Link
                    key={item.href}
                    href={href(locked(item) ? "/app/matches?choose_role=1" : item.href)}
                    aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
                    title={locked(item) ? t("chooseRoleFirst") : undefined}
                    aria-label={locked(item) ? `${t(item.key)} · ${t("chooseRoleFirst")}` : undefined}
                    onClick={() => setOpenedAt(null)}
                  >
                    <Icon size={22} strokeWidth={1.7} aria-hidden />
                    {t(item.key)}
                    {locked(item) ? <LockKeyhole size={14} aria-hidden /> : null}
                  </Link>
                );
              })}
              <Link href="/about" onClick={() => setOpenedAt(null)}>
                <BookOpen size={22} strokeWidth={1.7} aria-hidden />
                {t("about")}
              </Link>
            </div>
            <div className="a-sheet-row">
              {tools}
              <form method="post" action="/auth/logout">
                <button type="submit" className="a-link">
                  <LogOut size={16} aria-hidden /> {t("signOut")}
                </button>
              </form>
            </div>
            <button
              type="button"
              className="a-btn is-ghost is-block"
              style={{ marginTop: 14 }}
              onClick={dismiss}
            >
              {t("close")}
            </button>
          </div>
        </>
      ) : null}
    </>
  );
}
