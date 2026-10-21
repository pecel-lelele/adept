"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import type { NavItem } from "@/config/navigation";
import { SCENARIO_PARAM } from "@/lib/scenario";
import { cn } from "@/lib/utils";

/** Query params that describe "the same plan" and must survive navigation. */
const PRESERVED_PARAMS = [SCENARIO_PARAM, "role", "snapshot_date"] as const;

/** Journey steps 1-4 plus extra links; keeps ?scenario and ?role when navigating. */
export function JourneyStepper({ items }: { items: readonly NavItem[] }) {
  const t = useTranslations("common");
  const pathname = usePathname();
  const params = useSearchParams();
  const next = new URLSearchParams();
  for (const key of PRESERVED_PARAMS) {
    const value = params.get(key);
    if (value) next.set(key, value);
  }
  const query = next.toString();
  const suffix = query ? `?${query}` : "";

  return (
    <nav className="flex flex-wrap gap-1 text-sm">
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
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
              <span className="text-xs opacity-70">
                {t("journey.step", { n: item.step })}
              </span>
            ) : null}
            {t(`nav.${item.key}`)}
          </Link>
        );
      })}
    </nav>
  );
}
