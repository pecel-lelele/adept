import { getTranslations } from "next-intl/server";

import type { ScenarioId, Schemas } from "@/lib/api";

import { TrendLinesChart, type TrendLine } from "./TrendLinesChart";

type Series = Schemas["TrendSeriesResponse"];

/** Readable on white; the legend names every line, so colour is never the only cue. */
const COLORS = ["#16863e", "#b4483f", "#2563eb", "#9333ea", "#c2410c", "#0e7490", "#a16207", "#475569"] as const;

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/**
 * "Trend over time": pick a date range (native calendar pickers) and skills, then see each
 * skill's observed 7-day rolling share of sampled arXiv papers as a labelled line chart
 * (shadcn chart / Recharts). A plain GET form keeps the choice in the URL, so it works before
 * hydration and survives reloads.
 */
export async function TrendRangeCard({
  series,
  scenario,
  snapshotDate,
  pathname,
  allSkills,
}: {
  series: Series;
  scenario: ScenarioId;
  snapshotDate?: string;
  pathname: string;
  allSkills: { id: string; label: string }[];
}) {
  const t = await getTranslations("trends.range");
  const { lines, start, end } = series;
  const shown = new Set(lines.map((l) => l.skill_id));
  const chartLines: (TrendLine & { skillId: string })[] = lines.map((line, n) => ({
    skillId: line.skill_id,
    key: `s${n}`,
    label: line.label,
    color: COLORS[n % COLORS.length] ?? COLORS[0],
    change: line.change ?? null,
    points: line.points.map((p) => ({ day: p.day, share: p.share ?? null })),
  }));

  return (
    <section className="a-card" aria-labelledby="h-range">
      <div className="a-card-head">
        <h2 id="h-range">{t("title")}</h2>
      </div>
      <p className="a-card-sub">{t("hint", { days: series.window_days })}</p>

      <form className="a-range-form" action={pathname} method="get">
        <input type="hidden" name="scenario" value={scenario} />
        {snapshotDate ? <input type="hidden" name="snapshot_date" value={snapshotDate} /> : null}
        <label className="a-range-field">
          <span>{t("from")}</span>
          <input type="date" name="from" defaultValue={start} min={series.available_from ?? undefined} max={series.available_to ?? undefined} />
        </label>
        <label className="a-range-field">
          <span>{t("to")}</span>
          <input type="date" name="to" defaultValue={end} min={series.available_from ?? undefined} max={series.available_to ?? undefined} />
        </label>
        <fieldset className="a-range-skills">
          <legend>{t("skills")}</legend>
          {chartLines.map((line) => (
            <label key={line.skillId} className="a-range-chip" style={{ borderColor: line.color }}>
              <input type="checkbox" name="skill" value={line.skillId} defaultChecked />
              {line.label}
            </label>
          ))}
          <select name="skill" defaultValue="" aria-label={t("add")}>
            <option value="">{t("add")}</option>
            {allSkills.filter((s) => !shown.has(s.id)).map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </fieldset>
        <div className="a-range-actions">
          <button type="submit" className="a-btn">{t("show")}</button>
          <a className="a-btn is-ghost" href={`${pathname}?scenario=${scenario}`}>{t("reset")}</a>
        </div>
      </form>

      {!lines.length ? (
        <p className="a-muted a-small">{series.available_to ? t("emptyRange") : t("empty")}</p>
      ) : (
        <>
          <TrendLinesChart lines={chartLines} label={t("chartLabel", { from: start, to: end })} />
          <details className="a-small">
            <summary>{t("table")}</summary>
            <div className="a-range-table">
              <table>
                <caption className="a-sr">{t("chartLabel", { from: start, to: end })}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t("skill")}</th>
                    <th scope="col">{start}</th>
                    <th scope="col">{end}</th>
                    <th scope="col">{t("change")}</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line) => {
                    const known = line.points
                      .map((p) => p.share)
                      .filter((v): v is number => typeof v === "number");
                    const first = known[0];
                    const last = known[known.length - 1];
                    const delta = line.change;
                    return (
                      <tr key={line.skill_id}>
                        <th scope="row">{line.label}</th>
                        <td>{first === undefined ? "–" : pct(first)}</td>
                        <td>{last === undefined ? "–" : pct(last)}</td>
                        <td>{delta === null || delta === undefined ? "–" : `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(1)} pp`}</td>
                      </tr>
                    );
                  })}
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
