import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense, type ReactNode } from "react";

import type { NavItem } from "@/config/navigation";

import { JourneyStepper } from "../JourneyStepper";
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
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <Link href="/" className="font-semibold">
            {t("appName")}
          </Link>
          <span className="text-xs text-muted-foreground">{modeLabel}</span>
          <div className="ml-auto flex items-center gap-2">
            {showScenario ? (
              <Suspense>
                <ScenarioToggle />
              </Suspense>
            ) : null}
            <LocaleSwitcher />
          </div>
        </div>
        <div className="mx-auto max-w-5xl px-4 pb-2">
          <Suspense>
            <JourneyStepper items={nav} />
          </Suspense>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-5xl px-4 pb-6 text-xs text-muted-foreground">
        {t("humanInCharge")} ·{" "}
        <Link href="/about" className="underline">
          {t("nav.about")}
        </Link>
      </footer>
    </div>
  );
}
