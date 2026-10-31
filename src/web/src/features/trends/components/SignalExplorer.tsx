"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import type { ScenarioId, Schemas } from "@/lib/api";

const DIRS = ["all", "rising", "stable", "declining"] as const;
type Dir = (typeof DIRS)[number];
const PAGE_SIZE = 10;

/** Keep a bounded, stable page without fetching or rebuilding the selected snapshot. */
export function pageItems<T>(items: T[], requested: number): { items: T[]; page: number; pages: number } {
  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, requested), pages);
  return { items: items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), page, pages };
}

/** A bounded, instant explorer of one selected snapshot; each row opens its evidence. */
export function SignalExplorer({
  items,
  scenario,
}: {
  items: Schemas["SkillVelocity"][];
  scenario: ScenarioId;
}) {
  const t = useTranslations("common.design");
  const tp = useTranslations("ui.page");
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState<Dir>("all");
  const [requestedPage, setRequestedPage] = useState(1);
  const controls = useRef<HTMLDivElement>(null);
  const key = scenario === "fast" ? "direction_fast" : "direction_moderate";
  const velocity = scenario === "fast" ? "velocity_fast" : "velocity_moderate";
  const top = Math.max(0.01, ...items.map((i) => Math.abs(i[velocity])));
  const count = (d: Dir) => (d === "all" ? items.length : items.filter((i) => i[key] === d).length);
  const visible = items
    .filter((i) => i.skill_label.toLowerCase().includes(search.trim().toLowerCase()))
    .filter((i) => direction === "all" || i[key] === direction)
    .sort((a, b) => b[velocity] - a[velocity]);
  const { items: pageRows, page, pages } = pageItems(visible, requestedPage);
  const changePage = (next: number) => {
    setRequestedPage(next);
    controls.current?.scrollIntoView({
      block: "start",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });
  };

  return (
    <div className="a-explorer radar-skills">
      <div className="a-explorer-tools" ref={controls}>
        <label className="a-search">
          <Search size={15} aria-hidden />
          <input aria-label={t("search")} placeholder={t("search")} value={search} onChange={(e) => { setSearch(e.target.value); setRequestedPage(1); }} />
        </label>
        <div className="a-filterseg" role="radiogroup" aria-label={t("filters")}>
          {DIRS.map((d) => (
            <button key={d} type="button" role="radio" aria-checked={direction === d} onClick={() => { setDirection(d); setRequestedPage(1); }}>
              {d === "all" ? t("all") : t(d)} <span>{count(d)}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="a-rows" role="table" aria-label={tp("allSkills")}>
        <div className="a-rows-head" role="row">
          <span role="columnheader">{tp("colSkill")}</span>
          <span role="columnheader">{tp("colTrend")}</span>
          <span role="columnheader">{tp("colSignal")}</span>
          <span role="columnheader">{tp("colExposure")}</span>
        </div>
        {pageRows.map((i) => {
          const v = i[velocity];
          const dir = i[key];
          return (
            <details className="a-row" key={`${page}:${direction}:${search}:${i.skill_id}`} role="row">
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
                  <span className="a-mobile-metric-label">{tp("colSignal")}</span>
                  <span className="a-signal-track" aria-hidden>
                    <i data-dir={dir} data-side={v < 0 ? "left" : "right"} style={{ width: `${Math.max(2, (Math.abs(v) / top) * 50)}%` }} />
                  </span>
                  <b>{`${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(2)}`}</b>
                </span>
                <span role="cell" className="a-row-num">
                  <span className="a-mobile-metric-label">{tp("colExposure")}</span>
                  {i.automation_exposure.toFixed(2)}
                </span>
              </summary>
              <p>{i.labor_decay_source_note}</p>
            </details>
          );
        })}
        {!visible.length ? <p className="a-row-empty">{tp("noMatch")}</p> : null}
      </div>
      {pages > 1 ? (
        <nav className="a-list-pager" aria-label={tp("allSkills")}>
          <button type="button" className="a-btn is-ghost is-small" disabled={page === 1}
            onClick={() => changePage(page - 1)}>{tp("previousPage")}</button>
          <span role="status" aria-live="polite">{tp("pageOf", { page, pages })}</span>
          <button type="button" className="a-btn is-ghost is-small" disabled={page === pages}
            onClick={() => changePage(page + 1)}>{tp("nextPage")}</button>
        </nav>
      ) : null}
    </div>
  );
}
