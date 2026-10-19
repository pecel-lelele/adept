"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Mode = "individual" | "organisation";

const MODES = {
  individual: { start: "/app/onboarding", demo: "/demo/learner" },
  organisation: { start: "/org/setup", demo: "/demo/org" },
} as const;

/** Landing with the Individual | Organisation switch (Core, owner M4). */
export function LandingView({ freshness, localeSwitcher }: { freshness: ReactNode; localeSwitcher: ReactNode }) {
  const t = useTranslations("common");
  const [mode, setMode] = useState<Mode>("individual");

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-4 py-10">
      <header className="flex items-center justify-between">
        <span className="text-lg font-semibold">{t("appName")}</span>
        {localeSwitcher}
      </header>

      <div role="tablist" className="inline-flex self-start rounded-lg border p-1">
        {(Object.keys(MODES) as Mode[]).map((m) => (
          <button
            key={m}
            role="tab"
            type="button"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm transition-colors",
              mode === m ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {t(`landing.${m}`)}
          </button>
        ))}
      </div>

      <section className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight">{t(`landing.${mode}Title`)}</h1>
        <p className="text-lg text-muted-foreground">{t(`landing.${mode}Body`)}</p>
        <div className="flex flex-wrap gap-3">
          <Link href={MODES[mode].start} className={buttonVariants({ size: "lg" })}>
            {t(`landing.${mode}Cta`)}
          </Link>
          {/* Plain <a>: /demo/* are route handlers that set a cookie and redirect. */}
          <a href={MODES[mode].demo} className={buttonVariants({ size: "lg", variant: "outline" })}>
            {t(`landing.${mode}Demo`)}
          </a>
        </div>
        {freshness}
      </section>

      <p className="text-sm text-muted-foreground">{t("humanInCharge")}</p>
      <p className="text-xs text-muted-foreground">
        {t("tagline")} ·{" "}
        <Link href="/about" className="underline">
          {t("nav.about")}
        </Link>
      </p>
    </main>
  );
}
