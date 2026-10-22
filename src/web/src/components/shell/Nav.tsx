"use client";

import {
  BookOpen,
  ChevronDown,
  ChartNoAxesCombined,
  ClipboardCheck,
  Compass,
  Database,
  Grid3x3,
  House,
  Layers,
  Leaf,
  LogOut,
  Menu,
  MoreHorizontal,
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
};

function useHref() {
  const params = useSearchParams();
  return (href: string) => journeyHref(href, params);
}

function isCurrent(ws: Workspace, item: NavItem, pathname: string): boolean {
  return activeItem(ws, pathname)?.href === item.href;
}

/** Desktop sidebar: the journey always visible; everything else in one collapsible group. */
export function SideNav({ ws, doneSteps }: { ws: Workspace; doneSteps: number[] }) {
  const t = useTranslations("ui.nav");
  const pathname = usePathname();
  const href = useHref();
  const [primary, ...rest] = ws.groups;
  const extra = rest.flatMap((g) => g.items);
  const extraActive = extra.some((i) => isCurrent(ws, i, pathname));

  const link = (item: NavItem) => {
    const Icon = ICONS[item.icon];
    const done = item.step ? doneSteps.includes(item.step) : false;
    return (
      <Link
        key={item.href}
        href={href(item.href)}
        className="a-navlink"
        aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
      >
        <Icon size={18} strokeWidth={1.8} aria-hidden />
        {t(item.key)}
        {item.step ? (
          <span className="a-step" data-done={done}>
            {done ? "✓" : item.step}
          </span>
        ) : null}
      </Link>
    );
  };

  return (
    <nav aria-label={t(ws.mode === "organisation" ? "organisation" : "learner")} className="a-stack" style={{ gap: 6 }}>
      <div className="a-navgroup">{primary?.items.map(link)}</div>
      {extra.length ? (
        <details className="a-navmore" open={extraActive || undefined} key={extraActive ? "open" : "closed"}>
          <summary>
            <MoreHorizontal size={18} strokeWidth={1.8} aria-hidden />
            {t("more")}
            <ChevronDown size={16} className="a-chev" aria-hidden />
          </summary>
          <div className="a-navgroup">{extra.map(link)}</div>
        </details>
      ) : null}
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
export function TabBar({ ws, tools }: { ws: Workspace; tools: ReactNode }) {
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
      Array.from(sheet?.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), select, input") ?? []);
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

  return (
    <>
      <nav className="a-tabs" aria-label={t("journey")}>
        {tabs.map((item) => {
          const Icon = ICONS[item.icon];
          return (
            <Link
              key={item.href}
              href={href(item.href)}
              className="a-tab"
              aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
            >
              <span className="a-tab-icon">
                <Icon size={20} strokeWidth={1.8} aria-hidden />
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
                    href={href(item.href)}
                    aria-current={isCurrent(ws, item, pathname) ? "page" : undefined}
                    onClick={() => setOpenedAt(null)}
                  >
                    <Icon size={22} strokeWidth={1.7} aria-hidden />
                    {t(item.key)}
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
              <a href="/auth/logout" className="a-link">
                <LogOut size={16} aria-hidden /> {t("signOut")}
              </a>
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
