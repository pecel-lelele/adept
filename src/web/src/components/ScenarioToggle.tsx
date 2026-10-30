"use client";

import { Gauge, Rabbit, Turtle } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { parseScenario, SCENARIO_PARAM, SCENARIOS } from "@/lib/scenario";

import { onRadioKeyDown, radioTabIndex } from "./radioGroup";

const ICON = { moderate: Turtle, fast: Rabbit } as const;

/**
 * "AI pace" switch shown at the top right of the pages it changes. The value lives in the URL
 * (?scenario=moderate|fast); the full scenario names stay in each button's title.
 */
export function ScenarioToggle() {
  const t = useTranslations("common.scenario");
  const pathname = usePathname();
  const params = useSearchParams();
  const current = parseScenario(params.get(SCENARIO_PARAM) ?? undefined);
  const preserved = [...params.entries()].filter(([key]) => key !== SCENARIO_PARAM);

  return (
    <div className="a-stack" style={{ gap: 4, alignItems: "flex-end" }}>
      <form className="a-pace" action={pathname} method="get" title={t("hint")}>
        {/* A native GET replaces the document even if an RSC transition is stranded.
            Keep repeated filters and replay context; only replace the scenario. */}
        {preserved.map(([name, value], index) => (
          <input key={index} type="hidden" name={name} value={value} />
        ))}
        <span className="a-pace-label">
          <Gauge size={15} aria-hidden /> {t("pace")}
        </span>
        <div role="radiogroup" aria-label={t("label")} className="a-pace-seg">
          {SCENARIOS.map((s) => {
            const Icon = ICON[s];
            return (
              <button
                key={s}
                type="submit"
                name={SCENARIO_PARAM}
                value={s}
                role="radio"
                aria-checked={current === s}
                tabIndex={radioTabIndex(current === s)}
                title={t(s)}
                onClick={(e) => { if (s === current) e.preventDefault(); }}
                onKeyDown={(e) => onRadioKeyDown(e, SCENARIOS, current, (next) => {
                  if (next === current) return;
                  const button = e.currentTarget.form?.querySelector<HTMLButtonElement>(`button[value="${next}"]`);
                  if (button) button.form?.requestSubmit(button);
                })}
              >
                <Icon size={14} aria-hidden />
                {t(`${s}Short`)}
              </button>
            );
          })}
        </div>
      </form>
      <small className="a-small a-muted" style={{ maxWidth: 320, textAlign: "right" }}>{t("hint")}</small>
    </div>
  );
}
