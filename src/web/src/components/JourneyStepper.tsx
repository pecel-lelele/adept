"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import type { NavItem } from "@/config/navigation";
import { SCENARIO_PARAM } from "@/lib/scenario";
import { cn } from "@/lib/utils";

/** Journey steps 1-4 plus extra links; keeps ?scenario when navigating. */
export function JourneyStepper({ items }: { items: readonly NavItem[] }) {
  const t = useTranslations("common");
  const pathname = usePathname();
  const scenario = useSearchParams().get(SCENARIO_PARAM);
  const suffix = scenario ? `?${SCENARIO_PARAM}=${scenario}` : "";

  return (
    <nav className="flex flex-wrap gap-1 text-sm">
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={`${item.href}${suffix}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 transition-colors",
              active ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {item.step ? (
              <span className="text-xs opacity-70">{t("journey.step", { n: item.step })}</span>
            ) : null}
            {t(`nav.${item.key}`)}
          </Link>
        );
      })}
    </nav>
  );
}
