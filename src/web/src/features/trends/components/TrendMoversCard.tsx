import { ArrowUpRight, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { MetaBar } from "@/components";
import { ErrorState } from "@/components/ErrorState";
import type { ScenarioId, Schemas } from "@/lib/api";

import { fetchCompare } from "../api";
import { DEFAULT_PRESET, formatChange, PRESETS, type TrendPreset } from "../range";

type Line = Schemas["TrendCompareLine"];

function Movers({ title, icon, lines, link }: { title: string; icon: React.ReactNode; lines: Line[]; link: (line: Line) => string }) {
  return (
    <div>
      <h3 className="a-small a-range-movers-head">{icon} {title}</h3>
      <ul className="a-mini">
        {lines.map((line) => (
          <li key={line.entity}>
            <Link href={link(line)}>{line.label}</Link>
            <b>{typeof line.change === "number" ? formatChange(line.change, "raw") : "–"}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Home: the three biggest risers and fallers for the selected range, linking into the chart. */
export async function TrendMoversCard({
  scenario,
  preset,
  homeHref,
  radarHref,
}: {
  scenario: ScenarioId;
  preset?: string;
  /** Home link with the preset set; keeps the page's other choices. */
  homeHref: (preset: TrendPreset) => string;
  /** Radar link; keeps the journey's scenario and context. */
  radarHref: string;
}) {
  const t = await getTranslations("trends.range");
  const active = PRESETS.find((p) => p === preset) ?? DEFAULT_PRESET;
  const result = await fetchCompare({ kind: "skill", entities: [], preset: active, scenario, horizon: 90, mode: "raw" });
  const glue = radarHref.includes("?") ? "&" : "?";
  const link = (extra: string) => `${radarHref}${glue}view=skills&preset=${active}&mode=raw${extra}#trend`;
  if (!result.ok) return <ErrorState failure={result} compact />;
  const { lines, meta, available_to: through } = result.data;
  const rising = lines.filter((l) => (l.change ?? 0) > 0);
  const falling = lines.filter((l) => (l.change ?? 0) < 0);
  const lineHref = (line: Line) => link(`&entity=${encodeURIComponent(line.entity)}`);
  return (
    <section className="a-card" aria-labelledby="h-trend-movers">
      <div className="a-card-head">
        <h2 id="h-trend-movers"><TrendingUp size={16} aria-hidden /> {t("moversTitle")}</h2>
        <Link href={link("")}>{t("moversOpen")} <ArrowUpRight size={13} aria-hidden /></Link>
      </div>
      <div className="a-range-group" role="group" aria-label={t("presetLabel")}>
        {PRESETS.map((p) => (
          <Link key={p} className="a-range-toggle" aria-current={p === active ? "true" : undefined} href={homeHref(p)}>{t(`presets.${p}`)}</Link>
        ))}
      </div>
      {through ? <p className="a-small a-muted">{t("dataThrough", { date: through })}</p> : null}
      {lines.length ? (
        <div className="a-split">
          {rising.length ? <Movers title={t("risers")} icon={<TrendingUp size={14} aria-hidden />} lines={rising} link={lineHref} /> : null}
          {falling.length ? <Movers title={t("fallers")} icon={<TrendingDown size={14} aria-hidden />} lines={falling} link={lineHref} /> : null}
        </div>
      ) : (
        <p className="a-muted a-small">{through ? t("emptyRange") : t("empty")}</p>
      )}
      <MetaBar meta={meta} />
    </section>
  );
}
