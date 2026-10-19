"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { parseScenario, SCENARIO_PARAM, SCENARIOS } from "@/lib/scenario";
import { cn } from "@/lib/utils";

/** Global scenario switch; the value lives in the URL (?scenario=moderate|fast). */
export function ScenarioToggle() {
  const t = useTranslations("common.scenario");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const current = parseScenario(params.get(SCENARIO_PARAM) ?? undefined);

  function select(scenario: string) {
    const next = new URLSearchParams(params.toString());
    next.set(SCENARIO_PARAM, scenario);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  return (
    <div role="radiogroup" aria-label={t("label")} className="inline-flex rounded-md border p-0.5 text-xs">
      {SCENARIOS.map((s) => (
        <button
          key={s}
          type="button"
          role="radio"
          aria-checked={current === s}
          onClick={() => select(s)}
          className={cn(
            "rounded px-2 py-1 transition-colors",
            current === s ? "bg-primary text-primary-foreground" : "hover:bg-accent",
          )}
        >
          {t(s)}
        </button>
      ))}
    </div>
  );
}
