"use client";

import { Activity, Gauge, Zap } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { parseScenario, SCENARIO_PARAM, SCENARIOS } from "@/lib/scenario";

import { onRadioKeyDown, radioTabIndex } from "./radioGroup";

const ICON = { moderate: Activity, fast: Zap } as const;
/** Undo the busy look if the page never unloads (e.g. a failed request). */
const PENDING_RESET_MS = 20_000;

/** Marks the page busy while the next scenario loads (styled in adept.css). */
function markBusy(form: HTMLFormElement | null | undefined) {
  if (!form || typeof window === "undefined") return;
  setNavigating(form, true);
  window.setTimeout(() => setNavigating(form, false), PENDING_RESET_MS);
}

function setNavigating(form: HTMLFormElement | null, on: boolean) {
  if (on) document.documentElement.dataset.navigating = "true";
  else delete document.documentElement.dataset.navigating;
  form?.setAttribute("aria-busy", String(on));
}

if (typeof window !== "undefined") {
  // Back/forward can restore this page from the cache while it still looks busy.
  window.addEventListener("pageshow", () => {
    delete document.documentElement.dataset.navigating;
    document.querySelectorAll(".a-pace[aria-busy]").forEach((f) => f.setAttribute("aria-busy", "false"));
  });
}

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
    <div className="a-stack" style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
      <form
        className="a-pace"
        action={pathname}
        method="get"
        title={t("hint")}
      >
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
                onClick={(e) => {
                  if (s === current) e.preventDefault();
                  else markBusy((e.currentTarget as HTMLButtonElement | undefined)?.form); // never blocks the browser's own submit
                }}
                onKeyDown={(e) => onRadioKeyDown(e, SCENARIOS, current, (next) => {
                  if (next === current) return;
                  const button = e.currentTarget.form?.querySelector<HTMLButtonElement>(`button[value="${next}"]`);
                  if (button) {
                    markBusy(button.form);
                    button.form?.requestSubmit(button);
                  }
                })}
              >
                <Icon size={14} aria-hidden />
                {t(`${s}Short`)}
              </button>
            );
          })}
        </div>
      </form>
      <small className="a-small a-muted a-pace-idle" style={{ maxWidth: 320, textAlign: "right" }}>{t("hint")}</small>
      <small className="a-small a-pace-busy" role="status">{t("updating")}</small>
    </div>
  );
}
