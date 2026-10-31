import { getTranslations } from "next-intl/server";
import { ChartNoAxesCombined } from "lucide-react";

import { MetaBar } from "@/components";
import type { ScenarioId, Schemas } from "@/lib/api";

import { DEFAULT_HORIZON, formatChange, formatValue, HORIZONS, KIND_OF_VIEW, PRESETS, rangeHref, VIEWS, type TrendRange } from "../range";
import { TrendLinesChart, type TrendLine } from "./TrendLinesChart";

type Compare = Schemas["TrendCompareResponse"];

/** Readable on white; the legend names every line, so colour is never the only cue. */
const COLORS = ["#16863e", "#b4483f", "#2563eb", "#9333ea", "#c2410c", "#0e7490", "#a16207", "#475569"] as const;

/** Match the API's limits (`comparison.MAX_LINES`, `series.MAX_DAYS`). */
const MAX_LINES = 8;
const MAX_DAYS = 366;

/**
 * "Trend over time": skills, roles and categories over a stored date range, rebased to 100 or
 * as raw scores, with a dashed pace continuation for the selected scenario. Plain links and a
 * GET form keep every choice in the URL, so it works before hydration and survives reloads.
 */
export async function TrendRangeCard({
  data,
  range,
  scenario,
  snapshotDate,
  pathname,
  rejected = false,
}: {
  data: Compare;
  range: TrendRange;
  scenario: ScenarioId;
  snapshotDate?: string;
  pathname: string;
  rejected?: boolean;
}) {
  const t = await getTranslations("trends.range");
  const context = { scenario, snapshotDate };
  const href = (change: Partial<TrendRange>) => rangeHref(pathname, range, context, change);
  const { lines, start, end, mode } = data;
  const kind = KIND_OF_VIEW[range.view];
  const shown = new Set(lines.map((l) => l.entity));
  const custom = !range.preset;
  const chartLines: (TrendLine & { entity: string })[] = lines.map((line, n) => ({
    entity: line.entity,
    key: `s${n}`,
    label: line.label,
    color: COLORS[n % COLORS.length] ?? COLORS[0],
    change: line.change ?? null,
    points: line.points.map((p) => ({ day: p.day, value: p.value ?? null })),
    projection: line.projection.map((p) => ({ day: p.day, value: p.value ?? null })),
  }));
  // Roles and categories compare together; skills compare with skills.
  const pickable = data.options.filter((o) => (kind === "skill" ? o.kind === "skill" : o.kind !== "skill") && !shown.has(o.entity));
  const roleOptions = pickable.filter((o) => o.kind === "role");
  const categoryOptions = pickable.filter((o) => o.kind === "category");
  const skillOptions = pickable.filter((o) => o.kind === "skill");
  const derived = lines.some((l) => l.kind !== "skill") || (kind !== "skill" && !lines.length);
  const value = (v: number | null | undefined) => (typeof v === "number" ? formatValue(v, mode) : "–");
  const delta = (v: number | null | undefined) => (typeof v === "number" ? formatChange(v, mode) : "–");

  return (
    <section className="a-card" id="trend" aria-labelledby="h-range">
      <div className="a-card-head">
        <h2 id="h-range">{t("title")}</h2>
        {data.available_to ? <span className="a-small a-muted">{t("dataThrough", { date: data.available_to })}</span> : null}
      </div>
      <MetaBar meta={data.meta} />
      <p className="a-card-sub">{t("hint", { days: data.window_days })}</p>
      {rejected ? (
        <p className="a-small" role="alert">{t("rejected", { max: MAX_LINES, days: MAX_DAYS })}</p>
      ) : null}

      <nav className="a-range-group" aria-label={t("viewLabel")}>
        {VIEWS.map((view) => (
          <a key={view} className="a-range-toggle" aria-current={view === range.view ? "true" : undefined} href={href({ view, entities: [] })}>
            {t(`views.${view}`)}
          </a>
        ))}
      </nav>

      <div className="a-range-group" role="group" aria-label={t("presetLabel")}>
        {PRESETS.map((preset) => (
          <a key={preset} className="a-range-toggle" aria-current={preset === range.preset ? "true" : undefined} href={href({ preset, from: undefined, to: undefined })}>
            {t(`presets.${preset}`)}
          </a>
        ))}
        {custom ? <span className="a-range-toggle" aria-current="true">{t("presets.custom")}</span> : null}
      </div>

      <details className="a-range-editor" open={custom || rejected || range.entities.length > 0 || range.mode === "raw" || range.horizon !== DEFAULT_HORIZON}>
        <summary className="a-range-editor-summary">{t("adjust")}</summary>
        <div className="a-range-editor-body">
          <form className="a-range-form" action={`${pathname}#trend`} method="get">
            <input type="hidden" name="scenario" value={scenario} />
            <input type="hidden" name="view" value={range.view} />
            {snapshotDate ? <input type="hidden" name="snapshot_date" value={snapshotDate} /> : null}
            {range.mode === "raw" ? <input type="hidden" name="mode" value="raw" /> : null}
            {range.horizon !== 90 ? <input type="hidden" name="horizon" value={range.horizon} /> : null}
            <label className="a-range-field">
              <span>{t("from")}</span>
              <input type="date" name="from" defaultValue={start} min={data.available_from ?? undefined} max={data.available_to ?? undefined} />
            </label>
            <label className="a-range-field">
              <span>{t("to")}</span>
              <input type="date" name="to" defaultValue={end} min={data.available_from ?? undefined} max={data.available_to ?? undefined} />
            </label>
            <fieldset className="a-range-skills">
              <legend>{t(`legend.${range.view}`)}</legend>
              {chartLines.map((line) => (
                <label key={line.entity} className="a-range-chip" style={{ borderColor: line.color }}>
                  <input type="checkbox" name="entity" value={line.entity} defaultChecked />
                  {line.label}
                </label>
              ))}
              {chartLines.length < MAX_LINES ? (
                <select name="entity" defaultValue="" aria-label={t("add")}>
                  <option value="">{t("add")}</option>
                  {skillOptions.map((o) => <option key={o.entity} value={o.entity}>{o.label}</option>)}
                  {categoryOptions.length ? (
                    <optgroup label={t("views.categories")}>
                      {categoryOptions.map((o) => <option key={o.entity} value={o.entity}>{o.label}</option>)}
                    </optgroup>
                  ) : null}
                  {roleOptions.length ? (
                    <optgroup label={t("views.roles")}>
                      {roleOptions.map((o) => <option key={o.entity} value={o.entity}>{o.label}</option>)}
                    </optgroup>
                  ) : null}
                </select>
              ) : (
                <small className="a-muted">{t("limit", { max: MAX_LINES })}</small>
              )}
            </fieldset>
            <div className="a-range-actions">
              <button type="submit" className="a-btn">{t("show")}</button>
              <a className="a-btn is-ghost" href={href({ entities: [], from: undefined, to: undefined, preset: "3M" })}>{t("reset")}</a>
            </div>
          </form>

          <div className="a-range-controls">
            <div className="a-range-group" role="group" aria-label={t("modeLabel")}>
              <a className="a-range-toggle" aria-current={range.mode === "indexed" ? "true" : undefined} href={href({ mode: "indexed" })}>{t("modeIndexed")}</a>
              <a className="a-range-toggle" aria-current={range.mode === "raw" ? "true" : undefined} href={href({ mode: "raw" })}>{t("modeRaw")}</a>
            </div>
            <div className="a-range-group" role="group" aria-label={t("horizonLabel")}>
              <span className="a-small a-muted">{t("horizonLabel")}</span>
              {HORIZONS.map((horizon) => (
                <a key={horizon} className="a-range-toggle" aria-current={horizon === data.horizon_days ? "true" : undefined} href={href({ horizon })}>
                  {t(`horizons.h${horizon}`)}
                </a>
              ))}
            </div>
          </div>
        </div>
      </details>

      {!lines.length ? (
        <div className="a-range-empty" role="status">
          <ChartNoAxesCombined size={22} aria-hidden />
          <p>{!data.available_to ? t("empty") : !data.available_from ? t("emptyShort", { days: data.window_days }) : t("emptyRange")}</p>
        </div>
      ) : (
        <>
          {data.raw_fallback ? <p className="a-small" role="note">{t("rawFallback")}</p> : null}
          {mode === "indexed" && data.base_date ? <p className="a-small a-muted">{t("rebased", { date: data.base_date })}</p> : null}
          {derived ? <p className="a-small" role="note">{t("derived")}</p> : null}
          <TrendLinesChart
            lines={chartLines}
            mode={mode}
            label={t("chartLabel", { from: start, to: end })}
            projectedLabel={t("projected")}
            projectedFrom={data.projected_from}
          />
          <div className="a-range-table">
            <table>
              <caption className="a-sr">{t("statsCaption", { from: start, to: end })}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("line")}</th>
                  <th scope="col">{t("start")}</th>
                  <th scope="col">{t("end")}</th>
                  <th scope="col">{t("change")}</th>
                  <th scope="col">{t("moderateEnd", { days: data.horizon_days })}</th>
                  <th scope="col">{t("fastEnd", { days: data.horizon_days })}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => (
                  <tr key={line.entity}>
                    <th scope="row">{line.label}</th>
                    <td>{value(line.start_value)}</td>
                    <td>{value(line.end_value)}</td>
                    <td>{delta(line.change)}</td>
                    <td>{value(line.moderate_end)}</td>
                    <td>{value(line.fast_end)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.projection_meta ? (
            <div className="a-stack" style={{ gap: 6 }}>
              <p className="a-small">{t("projectionNote", { scenario: t(`scenario.${scenario}`), days: data.horizon_days })}</p>
              <MetaBar meta={data.projection_meta} />
            </div>
          ) : null}
          <details className="a-small">
            <summary>{t("table")}</summary>
            <div className="a-range-table">
              <table>
                <caption className="a-sr">{t("chartLabel", { from: start, to: end })}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t("day")}</th>
                    {lines.map((line) => (
                      <th key={line.entity} scope="col">{line.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(lines[0]?.points ?? []).map((point) => (
                    <tr key={point.day}>
                      <th scope="row">{point.day}</th>
                      {lines.map((line) => (
                        <td key={line.entity}>{value(line.points.find((p) => p.day === point.day)?.value)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <p className="a-small a-muted">{t("note")}</p>
        </>
      )}
    </section>
  );
}
