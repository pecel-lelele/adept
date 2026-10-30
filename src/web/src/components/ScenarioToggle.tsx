"use client";

import { Gauge, Rabbit, Turtle } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTransition } from "react";

import { parseScenario, SCENARIO_PARAM, SCENARIOS } from "@/lib/scenario";
import { useBusy } from "@/components/useBusy";

import { onRadioKeyDown, radioTabIndex } from "./radioGroup";

const ICON = { moderate: Turtle, fast: Rabbit } as const;

/**
 * "AI pace" switch shown at the top right of the pages it changes. The value lives in the URL
 * (?scenario=moderate|fast); the full scenario names stay in each button's title.
 */
export function ScenarioToggle() {
  const t = useTranslations("common.scenario");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  useBusy(pending);
  const current = parseScenario(params.get(SCENARIO_PARAM) ?? undefined);

  function select(scenario: string) {
    if (pending || scenario === current) return;
    const next = new URLSearchParams(params.toString());
    next.set(SCENARIO_PARAM, scenario);
    startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
  }

  return (
    <div className="a-stack" style={{ gap: 4, alignItems: "flex-end" }}>
      <div className="a-pace" aria-busy={pending} title={t("hint")}>
        <span className="a-pace-label">
          <Gauge size={15} aria-hidden /> {t("pace")}
        </span>
        <div role="radiogroup" aria-label={t("label")} className="a-pace-seg">
          {SCENARIOS.map((s) => {
            const Icon = ICON[s];
            return (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={current === s}
                // Not `disabled` while the route updates: that would drop keyboard focus.
                aria-disabled={pending || undefined}
                tabIndex={radioTabIndex(current === s)}
                title={t(s)}
                onClick={() => select(s)}
                onKeyDown={(e) => onRadioKeyDown(e, SCENARIOS, current, select)}
              >
                <Icon size={14} aria-hidden />
                {t(`${s}Short`)}
              </button>
            );
          })}
        </div>
      </div>
      <small className="a-small a-muted" style={{ maxWidth: 320, textAlign: "right" }}>{t("hint")}</small>
    </div>
  );
}
