"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";

import type { ScenarioId, Schemas } from "@/lib/api";
import { useBusy } from "@/components/useBusy";

const DIRS = ["all", "rising", "stable", "declining"] as const;
type Dir = (typeof DIRS)[number];

/** Every tracked skill: search, filter by direction, switch snapshot; each row opens its evidence. */
export function SignalExplorer({
  items,
  scenario,
  dates,
  date,
}: {
  items: Schemas["SkillVelocity"][];
  scenario: ScenarioId;
  dates: string[];
  date: string;
}) {
  const t = useTranslations("common.design");
  const tp = useTranslations("ui.page");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState<Dir>("all");
  const [pending, startTransition] = useTransition();
  useBusy(pending);
  const key = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const velocity = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const top = Math.max(0.01, ...items.map((i) => Math.abs(i[velocity])));
  const count = (d: Dir) => (d === "all" ? items.length : items.filter((i) => i[key] === d).length);
  const visible = items
    .filter((i) => i.skill_label.toLowerCase().includes(search.trim().toLowerCase()))
    .filter((i) => direction === "all" || i[key] === direction)
    .sort((a, b) => b[velocity] - a[velocity]);

  return (
    <div className="a-explorer" aria-busy={pending}>
      <div className="a-explorer-tools">
        <label className="a-search">
          <Search size={15} aria-hidden />
          <input aria-label={t("search")} placeholder={t("search")} value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <div className="a-filterseg" role="radiogroup" aria-label={t("filters")}>
          {DIRS.map((d) => (
            <button key={d} type="button" role="radio" aria-checked={direction === d} onClick={() => setDirection(d)}>
              {d === "all" ? t("all") : t(d)} <span>{count(d)}</span>
            </button>
          ))}
        </div>
        <label className="a-inline-select">
          {t("snapshot")}
          <select
            className="a-select is-small"
            value={date}
            disabled={pending}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              next.set("snapshot_date", e.target.value);
              startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
            }}
          >
            {[...dates].reverse().map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="a-rows" role="table" aria-label={tp("allSkills")}>
        <div className="a-rows-head" role="row">
          <span role="columnheader">{tp("colSkill")}</span>
          <span role="columnheader">{tp("colTrend")}</span>
          <span role="columnheader">{tp("colSignal")}</span>
          <span role="columnheader">{tp("colExposure")}</span>
        </div>
        {visible.map((i) => {
          const v = i[velocity];
          const dir = i[key];
          return (
            <details className="a-row" key={i.skill_id} role="row">
              <summary>
                <span role="cell" className="a-row-title">
                  {i.skill_label}
                </span>
                <span role="cell">
                  <span className="a-trend" data-dir={dir}>
                    {t(dir)}
                  </span>
                </span>
                <span role="cell" className="a-signal">
                  <span className="a-signal-track" aria-hidden>
                    <i data-dir={dir} data-side={v < 0 ? "left" : "right"} style={{ width: `${Math.max(2, (Math.abs(v) / top) * 50)}%` }} />
                  </span>
                  <b>{`${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(2)}`}</b>
                </span>
                <span role="cell" className="a-row-num">
                  {Math.round(i.automation_exposure * 100)}%
                </span>
              </summary>
              <p>{i.labor_decay_source_note}</p>
            </details>
          );
        })}
        {!visible.length ? <p className="a-row-empty">{tp("noMatch")}</p> : null}
      </div>
    </div>
  );
}
