"use client";

import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState, useTransition } from "react";

import type { ScenarioId, Schemas } from "@/lib/api";
import { useBusy } from "@/components/useBusy";

const LIMIT = 15;

const DIRS = ["all", "rising", "stable", "declining"] as const;
type Dir = (typeof DIRS)[number];

/** Every tracked skill: search, filter by direction, switch snapshot; each row opens its evidence. */
export function SignalExplorer({
  items,
  scenario,
  dates,
}: {
  items: Schemas["SkillVelocity"][];
  scenario: ScenarioId;
  dates: string[];
}) {
  const t = useTranslations("common.design");
  const tp = useTranslations("ui.page");
  const th = useTranslations("ui.home");
  const tr = useTranslations("trends");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState<Dir>("all");
  const [page, setPage] = useState(1);
  const controls = useRef<HTMLDivElement>(null);
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
  const pageCount = Math.max(1, Math.ceil(visible.length / LIMIT));
  const currentPage = Math.min(page, pageCount);
  const offset = (currentPage - 1) * LIMIT;
  const changePage = (next: number) => {
    setPage(Math.max(1, Math.min(pageCount, next)));
    controls.current?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  };

  return (
    <div className="a-explorer radar-skills" aria-busy={pending}>
      <div className="a-explorer-tools" ref={controls}>
        <label className="a-search">
          <Search size={15} aria-hidden />
          <input aria-label={t("search")} placeholder={t("search")} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </label>
        <div className="a-filterseg" role="group" aria-label={t("filters")}>
          {DIRS.map((d) => (
            <button key={d} type="button" aria-pressed={direction === d} onClick={() => { setDirection(d); setPage(1); }}>
              {d === "all" ? t("all") : t(d)} <span>{count(d)}</span>
            </button>
          ))}
        </div>
        <label className="a-inline-select">
          {tr("dataEdition")}
          <select
            className="a-select is-small"
            value={params.get("snapshot_date") ?? ""}
            disabled={pending}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("snapshot_date", e.target.value);
              else next.delete("snapshot_date");
              startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
            }}
          >
            <option value="">{th("latest")}</option>
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
        {visible.slice(offset, offset + LIMIT).map((i) => {
          const v = i[velocity];
          const dir = i[key];
          return (
            <details className="a-row" key={`${currentPage}:${direction}:${search}:${i.skill_id}`} role="row">
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
                    <i data-dir={dir} data-side={v < 0 ? "left" : "right"} style={{ width: `${(Math.abs(v) / top) * 50}%` }} />
                  </span>
                  <b>{`${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(2)}`}</b>
                </span>
                <span role="cell" className="a-row-num">
                  {i.automation_exposure.toFixed(2)}
                </span>
              </summary>
              <p>{i.labor_decay_source_note}</p>
            </details>
          );
        })}
        {!visible.length ? <p className="a-row-empty">{tp("noMatch")}</p> : null}
      </div>
      <footer className="radar-pagination">
        <span aria-live="polite">{tr("pagination.range", { from: visible.length ? offset + 1 : 0, to: Math.min(offset + LIMIT, visible.length), total: visible.length })}</span>
        <nav aria-label={tr("pagination.label")}>
          <button type="button" aria-label={tr("pagination.previous")} disabled={currentPage === 1} onClick={() => changePage(currentPage - 1)}><ChevronLeft size={16} aria-hidden /></button>
          <span aria-live="polite">{tr("pagination.page", { page: currentPage, total: pageCount })}</span>
          <button type="button" aria-label={tr("pagination.next")} disabled={currentPage === pageCount} onClick={() => changePage(currentPage + 1)}><ChevronRight size={16} aria-hidden /></button>
        </nav>
      </footer>
    </div>
  );
}
