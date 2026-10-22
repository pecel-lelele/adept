"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTransition } from "react";

import { parseScenario, SCENARIO_PARAM, SCENARIOS } from "@/lib/scenario";

/** Global scenario switch; the value lives in the URL (?scenario=moderate|fast). */
export function ScenarioToggle() {
  const t = useTranslations("common.scenario");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const current = parseScenario(params.get(SCENARIO_PARAM) ?? undefined);

  function select(scenario: string) {
    const next = new URLSearchParams(params.toString());
    next.set(SCENARIO_PARAM, scenario);
    startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
  }

  return (
    <div role="radiogroup" aria-label={t("label")} className="a-seg" aria-busy={pending}>
      {SCENARIOS.map((s) => (
        <button
          key={s}
          type="button"
          role="radio"
          aria-checked={current === s}
          disabled={pending}
          onClick={() => select(s)}
        >
          {t(s)}
        </button>
      ))}
    </div>
  );
}
