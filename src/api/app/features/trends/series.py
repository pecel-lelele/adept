"""Rolling skill shares over a chosen date range, counted from the stored paper cache (M1-018).

Observed measurements, not forecasts: each point is the share of sampled arXiv cs.AI papers in
the 7 days ending that day that mention the skill. No model or network call is made.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.trends import TrendSeriesLine, TrendSeriesPoint, TrendSeriesResponse
from app.core import refdata
from app.core.errors import AppError
from app.features.data_refresh import trend_store

ARXIV_API = "https://export.arxiv.org/api/query"  # same source as data_refresh.measurements
# Versioned method inspected on this date; not an arXiv acquisition or observation date.
EMPTY_SOURCE = Source(
    name="Adept trend-series method (no stored paper observations)",
    url="https://github.com/pecel-lelele/adept/blob/"
    "8ecc82fc9dc36d88ebca49e0a665d832bee2a381/src/api/app/features/trends/series.py",
    retrieved_at=date(2026, 10, 31),
)

WINDOW = 7
# Mirrored by the chart's date limits (web: TrendRangeCard MAX_DAYS). Covers all of 2026.
MAX_DAYS = 366
MAX_SKILLS = 8
DEFAULT_DAYS = 28
DEFAULT_MOVERS = 3  # rising and falling each, when no skills are chosen


def rolling_shares(
    days: Sequence[date],
    papers: Mapping[date, int],
    mentions: Mapping[tuple[date, str], int],
    skill_id: str,
    window: int = WINDOW,
) -> list[float | None]:
    """Share per day over the `window` days ending that day; None unless all are stored."""
    out: list[float | None] = []
    for day in days:
        span = [day - timedelta(days=i) for i in range(window)]
        if any(d not in papers for d in span):
            out.append(None)
            continue
        total = sum(papers[d] for d in span)
        hits = sum(mentions.get((d, skill_id), 0) for d in span)
        out.append(round(hits / total, 6) if total else None)
    return out


def change(values: Sequence[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    return round(known[-1] - known[0], 6) if len(known) >= 2 else None


def _invalid(message: str) -> AppError:
    return AppError(message, status_code=422, code="invalid_range")


def default_start(
    end: date, stored: tuple[date, date, date] | None, first_full: date | None
) -> date:
    """Latest DEFAULT_DAYS with data. While fewer than WINDOW days are stored, default to the
    stored days (shown as gaps) rather than a start after the end."""
    floor = first_full if first_full and first_full <= end else (stored[0] if stored else end)
    return max(end - timedelta(days=DEFAULT_DAYS - 1), min(floor, end))


def get_series(
    start: date | None,
    end: date | None,
    skill_ids: list[str],
    scenario: ScenarioId,
) -> TrendSeriesResponse:
    labels = {r["id"]: r["label"] for r in refdata.rows("taxonomy", "skills")}
    unknown = [s for s in skill_ids if s not in labels]
    if unknown:
        raise _invalid(f"Unknown skills: {', '.join(unknown[:3])}.")
    if len(set(skill_ids)) > MAX_SKILLS:
        raise _invalid(f"Choose at most {MAX_SKILLS} skills.")
    stored = trend_store.stored_range()
    first_full = stored[0] + timedelta(days=WINDOW - 1) if stored else None
    newest = stored[1] if stored else None
    end = end or newest or date.today()
    if start is None:
        start = default_start(end, stored, first_full)
    if start > end:
        raise _invalid("The start date must be on or before the end date.")
    if (end - start).days + 1 > MAX_DAYS:
        raise _invalid(f"Choose a range of at most {MAX_DAYS} days.")
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    lines: list[TrendSeriesLine] = []
    if stored:
        chosen = list(dict.fromkeys(skill_ids)) or list(labels)
        papers, mentions = trend_store.daily(start - timedelta(days=WINDOW - 1), end, chosen)
        built = []
        for sid in chosen:
            values = rolling_shares(days, papers, mentions, sid)
            points = [TrendSeriesPoint(day=d, share=v) for d, v in zip(days, values, strict=True)]
            built.append(
                TrendSeriesLine(
                    skill_id=sid, label=labels[sid], points=points, change=change(values)
                )
            )
        if skill_ids:
            lines = built
        else:
            moved = sorted((x for x in built if x.change), key=lambda x: x.change or 0.0)
            rising = [x for x in reversed(moved) if (x.change or 0) > 0][:DEFAULT_MOVERS]
            falling = [x for x in moved if (x.change or 0) < 0][:DEFAULT_MOVERS]
            lines = rising + falling
    source = (
        Source(name="arXiv cs.AI submission API", url=ARXIV_API, retrieved_at=stored[2])
        if stored
        else EMPTY_SOURCE.model_copy()
    )
    # The papers actually counted: from the first plotted window's first day to the last
    # plotted day. Nothing plotted means no observation period.
    plotted = sorted({p.day for line in lines for p in line.points if p.share is not None})
    meta = RecommendationMeta(
        sources=[source],
        snapshot_date=min(end, newest) if newest else source.retrieved_at,
        scenario=scenario,
        is_estimate=False,  # observed sample counts, not a forecast
        observed_from=plotted[0] - timedelta(days=WINDOW - 1) if plotted else None,
        observed_to=plotted[-1] if plotted else None,
    )
    return TrendSeriesResponse(
        start=start,
        end=end,
        window_days=WINDOW,
        # With fewer than WINDOW days stored no window is complete, so there is no valid first day.
        available_from=first_full if first_full and newest and first_full <= newest else None,
        available_to=newest,
        lines=lines,
        meta=meta,
    )
