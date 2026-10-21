"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import type { NavItem } from "@/config/navigation";
import { journeyHref } from "@/lib/navigation";

export function WorkspaceNavigation({ nav }: { nav: readonly NavItem[] }) {
  const path = usePathname(),
    source = useSearchParams(),
    t = useTranslations("common");
  const params = new URLSearchParams(source);
  if (path.startsWith("/app/matches/"))
    params.set("role", decodeURIComponent(path.split("/")[3] ?? ""));
  return (
    <nav aria-label="Workspace" className="workspace-nav">
      {nav.map((item, index) => {
        const root = item.href === "/app" || item.href === "/org";
        const active =
          path === item.href || (!root && path.startsWith(item.href + "/"));
        return (
          <Link
            key={item.href}
            href={journeyHref(item.href, params)}
            aria-current={active ? "page" : undefined}
          >
            <span className="nav-mark" aria-hidden>
              {String(index + 1).padStart(2, "0")}
            </span>
            {t(`nav.${item.key}`)}
          </Link>
        );
      })}
    </nav>
  );
}
export function JourneyControls() {
  const path = usePathname(),
    source = useSearchParams(),
    t = useTranslations("common.workspace");
  const params = new URLSearchParams(source);
  if (path.startsWith("/app/matches/"))
    params.set("role", decodeURIComponent(path.split("/")[3] ?? ""));
  const base = path.startsWith("/org") ? "/org" : "/app";
  const routes =
    base === "/org"
      ? [
          "/org",
          "/org/setup",
          "/org/members",
          "/org/radar",
          "/org/gaps",
          "/org/plan",
          "/org/verify",
          "/org/sdg",
        ]
      : [
          "/app",
          "/app/onboarding",
          "/app/profile",
          "/app/radar",
          "/app/matches",
          "/app/pathway",
          "/app/progress",
          "/app/sdg",
        ];
  const exact = routes.indexOf(path);
  const index =
    exact >= 0
      ? exact
      : routes.findIndex((r) => r !== base && path.startsWith(r + "/"));
  const previous = path.startsWith("/app/matches/")
    ? "/app/matches"
    : path === "/app/pathway/compare"
      ? "/app/pathway"
      : (routes[Math.max(0, index - 1)] ?? base);
  const next = index >= 0 ? routes[index + 1] : undefined;
  return (
    <div className="journey-controls">
      <Link href={journeyHref(previous, params)}>
        ← {index <= 0 ? t("overview") : t("previous")}
      </Link>
      <span>{t("context")}</span>
      <Link href={journeyHref(next ?? base, params)}>
        {t(next ? "next" : "overview")} →
      </Link>
    </div>
  );
}
