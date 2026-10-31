import type { Schemas } from "@/lib/api";

export type TrendKind = Schemas["TrendCompareResponse"]["kind"];
export type TrendMode = Schemas["TrendCompareResponse"]["mode"];
export type TrendPreset = "1W" | "1M" | "3M" | "6M";
export type TrendView = "skills" | "roles" | "categories";

/** Everything the "Trend over time" card shows; it all lives in the URL. */
export type TrendRange = {
  view: TrendView;
  preset?: TrendPreset;
  from?: string;
  to?: string;
  entities: string[];
  mode: TrendMode;
  horizon: number;
};

export const VIEWS: readonly TrendView[] = ["skills", "roles", "categories"];
export const PRESETS: readonly TrendPreset[] = ["1W", "1M", "3M", "6M"];
export const HORIZONS = [30, 90, 180, 365] as const;
export const DEFAULT_HORIZON = 90;
export const DEFAULT_PRESET: TrendPreset = "3M";
export const KIND_OF_VIEW: Record<TrendView, TrendKind> = { skills: "skill", roles: "role", categories: "category" };

type Params = Record<string, string | string[] | undefined>;

const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);
const all = (value: string | string[] | undefined) => (Array.isArray(value) ? value : value ? [value] : []);

/** Unknown values fall back to defaults; the API still validates every date and entity. */
export function parseTrendRange(params: Params): TrendRange {
  const rawView = first(params.view);
  const view = VIEWS.find((v) => v === rawView) ?? "skills";
  const from = first(params.from) || undefined;
  const to = first(params.to) || undefined;
  const rawPreset = first(params.preset);
  const preset = PRESETS.find((p) => p === rawPreset) ?? (from || to ? undefined : DEFAULT_PRESET);
  const horizon = Number(first(params.horizon));
  return {
    view,
    preset,
    from,
    to,
    // `skill=` links from before roles and categories existed keep working.
    entities: [...new Set([...all(params.entity).filter(Boolean), ...all(params.skill).filter(Boolean).map((id) => `skill:${id}`)])],
    mode: first(params.mode) === "raw" ? "raw" : "indexed",
    horizon: HORIZONS.find((h) => h === horizon) ?? DEFAULT_HORIZON,
  };
}

/** A radar link for a changed range, keeping the rest of the state. */
export function rangeHref(
  pathname: string,
  range: TrendRange,
  context: { scenario: string; snapshotDate?: string },
  change: Partial<TrendRange>,
): string {
  const next = { ...range, ...change };
  const query = new URLSearchParams({ scenario: context.scenario, view: next.view });
  if (context.snapshotDate) query.set("snapshot_date", context.snapshotDate);
  if (next.preset) query.set("preset", next.preset);
  if (next.from) query.set("from", next.from);
  if (next.to) query.set("to", next.to);
  if (next.mode === "raw") query.set("mode", "raw");
  if (next.horizon !== DEFAULT_HORIZON) query.set("horizon", String(next.horizon));
  for (const entity of next.entities) query.append("entity", entity);
  return `${pathname}?${query.toString()}#trend`;
}

export const formatValue = (value: number, mode: TrendMode) => (mode === "raw" ? `${(value * 100).toFixed(1)}%` : value.toFixed(1));
export function formatChange(value: number, mode: TrendMode) {
  const sign = value > 0 ? "+" : "";
  return mode === "raw" ? `${sign}${(value * 100).toFixed(1)} pp` : `${sign}${value.toFixed(1)}`;
}
