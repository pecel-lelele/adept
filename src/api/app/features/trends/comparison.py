"""Trend over time for skills, roles and categories: compare, rebase and project (M1-025).

Counted from the stored paper cache only; no model or network call is made, on any range.

- Skill line: the observed 7-day rolling share (`series.rolling_shares`).
- Role line: per day, the importance-weighted average of its skills' shares (`role_skills.csv`).
  Empty if any of its skills has no value that day. Derived from arXiv skill signals; it is not
  observed role demand.
- Category line: the equal-weight mean of its roles (`role_categories.csv`). Roles without a
  skill profile have no line and are left out of the mean rather than emptying the category.
- Rebase: 100 at the first date where every line is above 0; raw scores if no such date exists.
- Projection: the radar's own moderate and fast velocities (`pipelines.trends.score`) from the
  last two 7-day windows, continued from the last observed day: `share * (1 + v * days / 7)`,
  kept between 0 and 1. `v` is per 7-day step because research velocity compares consecutive
  7-day windows. A pace continuation, never a prediction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import get_args

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.trends import (
    CompareMode,
    TrendCompareLine,
    TrendCompareOption,
    TrendComparePoint,
    TrendCompareResponse,
    TrendEntityKind,
    TrendRangePreset,
)
from app.core import refdata, seed
from app.features.data_refresh import trend_store
from app.features.trends.series import (
    ARXIV_API,
    DEFAULT_MOVERS,
    EMPTY_SOURCE,
    MAX_DAYS,
    WINDOW,
    _invalid,
    change,
    default_start,
    rolling_shares,
)

MAX_LINES = 8
NEUTRAL_EXPOSURE = 0.5  # score.DEFAULT_EXPOSURE, for skills without a curated coefficient
DEFAULT_HORIZON = 90
MAX_HORIZON = 365
# Above this many days points are weekly. A gap is at least a full 7-day window, so a weekly
# sample can never step over one.
DAILY_POINTS_UP_TO = 120
WEEKLY_STEP = 7
PRESET_DAYS: dict[str, int] = {"1W": 7, "1M": 30, "3M": 90, "6M": 180}
Shares = dict[str, list[float | None]]

assert set(PRESET_DAYS) == set(get_args(TrendRangePreset))


# ---------------------------------------------------------------------------
# Pure scoring
# ---------------------------------------------------------------------------


def weighted_line(
    shares: Mapping[str, Sequence[float | None]], weights: Mapping[str, float]
) -> list[float | None]:
    """Importance-weighted average per day; None when any weighted skill has no value."""
    total = sum(weights.values())
    if not weights or total <= 0:
        return []
    length = len(next(iter(shares.values()), []))
    out: list[float | None] = []
    for i in range(length):
        values = [shares[sid][i] for sid in weights]
        if any(v is None for v in values):
            out.append(None)
            continue
        known = [v for v in values if v is not None]
        out.append(
            round(sum(v * w for v, w in zip(known, weights.values(), strict=True)) / total, 6)
        )
    return out


def mean_line(lines: Sequence[Sequence[float | None]]) -> list[float | None]:
    """Equal-weight mean per day; None when any line has no value."""
    if not lines:
        return []
    out: list[float | None] = []
    for values in zip(*lines, strict=True):
        known = [v for v in values if v is not None]
        out.append(round(sum(known) / len(values), 6) if len(known) == len(values) else None)
    return out


def rebase_index(lines: Sequence[Sequence[float | None]]) -> int | None:
    """Index of the first date where every line is above 0, or None if there is none."""
    if not lines:
        return None
    for i in range(len(lines[0])):
        if all((line[i] or 0.0) > 0 for line in lines):
            return i
    return None


def indexed(value: float | None, base: float) -> float | None:
    return None if value is None else round(value / base * 100, 2)


def project(share: float, velocity: float, days: int) -> float:
    """Pace continuation, kept to a possible share (0 to 1)."""
    return max(0.0, min(1.0, share * (1 + velocity * days / WINDOW)))


def scenario_velocities(
    previous: float, current: float, labor_decay: float, exposure: float
) -> dict[ScenarioId, float]:
    """The radar's own definition of both scenarios (pipelines/trends/score.py)."""
    from pipelines.trends import score

    raw = score.composite_velocity(score.research_velocity(previous, current), labor_decay)
    return {"moderate": score.scenario_moderate(raw), "fast": score.scenario_fast(raw, exposure)}


def sampled_indexes(length: int) -> list[int]:
    """Every day up to DAILY_POINTS_UP_TO, else weekly counted back from the last day."""
    if length <= DAILY_POINTS_UP_TO:
        return list(range(length))
    # Keep the first observed value even when weekly points align from the last day.
    return sorted({0, *range(length - 1, -1, -WEEKLY_STEP)})


def horizon_days(horizon: int) -> list[int]:
    """Days ahead to plot: enough points for a straight, clamped line at any horizon."""
    step = max(1, horizon // 30)
    return sorted({*range(step, horizon + 1, step), horizon})


# ---------------------------------------------------------------------------
# Catalogue: roles and categories from reviewed seed files, never created at runtime
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entity:
    key: str  # "kind:id", the URL and API form
    kind: TrendEntityKind
    entity_id: str
    label: str
    skills: tuple[tuple[str, float], ...] = ()  # role: (skill, importance)
    roles: tuple[str, ...] = ()  # category: its roles that have a skill profile


@lru_cache(maxsize=1)
def _category_rows() -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (r["role_id"], r["category_id"], r["category_label"])
        for r in seed.rows("taxonomy", "role_categories")
    )


def catalogue() -> dict[str, Entity]:
    """Every chartable entity. Roles without a skill profile cannot have a line."""
    out: dict[str, Entity] = {}
    for row in refdata.rows("taxonomy", "skills"):
        out[f"skill:{row['id']}"] = Entity(f"skill:{row['id']}", "skill", row["id"], row["label"])
    weights: dict[str, list[tuple[str, float]]] = {}
    for row in refdata.rows("taxonomy", "role_skills"):
        weights.setdefault(row["role_id"], []).append((row["skill_id"], float(row["importance"])))
    labels = {row["id"]: row["label"] for row in refdata.rows("taxonomy", "roles")}
    for role_id, label in labels.items():
        if weights.get(role_id):
            key = f"role:{role_id}"
            out[key] = Entity(key, "role", role_id, label, skills=tuple(weights[role_id]))
    grouped: dict[str, tuple[str, list[str]]] = {}
    for role_id, category_id, category_label in _category_rows():
        members = grouped.setdefault(category_id, (category_label, []))[1]
        if f"role:{role_id}" in out:
            members.append(role_id)
    for category_id, (label, members) in grouped.items():
        if members:
            key = f"category:{category_id}"
            out[key] = Entity(key, "category", category_id, label, roles=tuple(members))
    return out


def _skills_of(entity: Entity, known: Mapping[str, Entity]) -> set[str]:
    if entity.kind == "skill":
        return {entity.entity_id}
    if entity.kind == "role":
        return {sid for sid, _weight in entity.skills}
    return {sid for role in entity.roles for sid, _weight in known[f"role:{role}"].skills}


def _line(entity: Entity, shares: Shares, known: Mapping[str, Entity]) -> list[float | None]:
    if entity.kind == "skill":
        return shares[entity.entity_id]
    if entity.kind == "role":
        return weighted_line(shares, dict(entity.skills))
    return mean_line([weighted_line(shares, dict(known[f"role:{r}"].skills)) for r in entity.roles])


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


def _resolve_range(
    preset: TrendRangePreset | None,
    start: date | None,
    end: date | None,
    stored: tuple[date, date, date] | None,
) -> tuple[date, date, date | None, date | None]:
    first_full = stored[0] + timedelta(days=WINDOW - 1) if stored else None
    newest = stored[1] if stored else None
    available_from = first_full if first_full and newest and first_full <= newest else None
    if stored is None:
        # Nothing stored: nothing is plotted and no date is claimed as data.
        end = end or EMPTY_SOURCE.retrieved_at
        start = start or end
        if start > end:
            raise _invalid("The start date must be on or before the end date.")
        if (end - start).days + 1 > MAX_DAYS:
            raise _invalid(f"Choose a range of at most {MAX_DAYS} days.")
        return start, end, None, None
    end = end or newest
    assert end is not None and newest is not None
    # Reject an out-of-store date before subtracting a preset span: a year-one query
    # must be a 422, not a date-underflow 500.
    if end < stored[0] or end > newest:
        raise _invalid(f"Choose dates between {available_from or stored[0]} and {newest}.")
    if preset:
        floor = available_from or stored[0]
        start = max(end - timedelta(days=PRESET_DAYS[preset] - 1), floor)
    elif start is None:
        start = default_start(end, stored, first_full)
    if start > end:
        raise _invalid("The start date must be on or before the end date.")
    if (end - start).days + 1 > MAX_DAYS:
        raise _invalid(f"Choose a range of at most {MAX_DAYS} days.")
    if available_from and (start < available_from or end > newest):
        raise _invalid(f"Choose dates between {available_from} and {newest}.")
    if available_from is None and (start < stored[0] or end > newest):
        raise _invalid(f"Choose dates between {stored[0]} and {newest}.")
    return start, end, available_from, newest


def _choose(
    kind: TrendEntityKind, entities: list[str], known: Mapping[str, Entity]
) -> tuple[list[Entity], bool]:
    """Requested entities, or every entity of `kind` for the movers view."""
    wanted = list(dict.fromkeys(entities))
    unknown = [key for key in wanted if key not in known]
    if unknown:
        raise _invalid(f"Unknown entities: {', '.join(unknown[:3])}.")
    if len(wanted) > MAX_LINES:
        raise _invalid(f"Choose at most {MAX_LINES} lines.")
    chosen = [known[key] for key in wanted]
    if any(e.kind == "skill" for e in chosen) and any(e.kind != "skill" for e in chosen):
        raise _invalid("Skills compare with skills; roles and categories compare together.")
    return (chosen, False) if chosen else ([e for e in known.values() if e.kind == kind], True)


def _movers(entities: list[Entity], values: Mapping[str, list[float | None]]) -> list[Entity]:
    moved = sorted(
        ((e, change(values[e.key])) for e in entities),
        key=lambda pair: pair[1] or 0.0,
    )
    rising = [e for e, c in reversed(moved) if (c or 0) > 0][:DEFAULT_MOVERS]
    falling = [e for e, c in moved if (c or 0) < 0][:DEFAULT_MOVERS]
    return rising + falling


def _empty_source() -> Source:
    return EMPTY_SOURCE.model_copy()


def get_compare(
    kind: TrendEntityKind,
    entities: list[str],
    preset: TrendRangePreset | None,
    start: date | None,
    end: date | None,
    scenario: ScenarioId,
    horizon: int,
    mode: CompareMode,
) -> TrendCompareResponse:
    known = catalogue()
    chosen, movers = _choose(kind, entities, known)
    stored = trend_store.stored_range()
    start, end, available_from, newest = _resolve_range(preset, start, end, stored)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    options = [TrendCompareOption(entity=e.key, kind=e.kind, label=e.label) for e in known.values()]
    derived = any(e.kind != "skill" for e in chosen)
    source = (
        Source(name="arXiv cs.AI submission API", url=ARXIV_API, retrieved_at=stored[2])
        if stored
        else _empty_source()
    )

    def meta(observed: list[date]) -> RecommendationMeta:
        return RecommendationMeta(
            sources=[source],
            snapshot_date=min(end, newest) if newest else source.retrieved_at,
            scenario=scenario,
            # Counted shares are observed; a role or category score is computed from them.
            is_estimate=derived,
            observed_from=observed[0] - timedelta(days=WINDOW - 1) if observed else None,
            observed_to=observed[-1] if observed else None,
        )

    def empty(lines: list[TrendCompareLine]) -> TrendCompareResponse:
        return TrendCompareResponse(
            kind=kind,
            start=start,
            end=end,
            window_days=WINDOW,
            step_days=1,
            available_from=available_from,
            available_to=newest,
            mode="raw" if mode == "raw" else "indexed",
            horizon_days=horizon,
            lines=lines,
            options=options,
            meta=meta([]),
        )

    if not stored:
        return empty([])

    # Enough earlier days for the first window and for the projection's previous window.
    wanted = sorted({sid for e in chosen for sid in _skills_of(e, known)})
    papers, mentions = trend_store.daily(start - timedelta(days=WINDOW * 2 - 1), end, wanted)
    shares: Shares = {sid: rolling_shares(days, papers, mentions, sid) for sid in wanted}
    # A skill line always has every day; a role reads only its own skills from `shares`.
    values = {e.key: _line(e, shares, known) for e in chosen}
    picked = _movers(chosen, values) if movers else chosen
    plotted = [
        day
        for i, day in enumerate(days)
        if any(values[e.key] and values[e.key][i] is not None for e in picked)
    ]
    if not picked or not plotted:
        return empty([])

    series = [values[e.key] for e in picked]
    base_at = rebase_index(series) if mode == "indexed" else None
    shown: CompareMode = "indexed" if base_at is not None else "raw"
    bases = {e.key: values[e.key][base_at] or 1.0 for e in picked} if base_at is not None else {}

    def scale(entity: Entity, value: float | None) -> float | None:
        return indexed(value, bases[entity.key]) if shown == "indexed" else value

    last = plotted[-1]
    prior = last - timedelta(days=WINDOW)
    at = rolling_window_shares(prior, last, papers, mentions, wanted)
    # The API process may be deployed without the offline pipelines package; the observed lines
    # still render, and no projection is ever made up without the radar's own method.
    try:
        from pipelines.trends import run as pipeline
        from pipelines.trends import score
    except ImportError:
        at = None
    decay = score.load_labor_decay() if at else {}
    exposure = score.load_automation_exposure() if at else {}
    can_project = at is not None
    ahead = horizon_days(horizon)
    keep = sampled_indexes(len(days))
    lines: list[TrendCompareLine] = []
    for entity in picked:
        raw = values[entity.key]
        known_values = [scale(entity, v) for v in raw if v is not None]
        endpoints: dict[ScenarioId, list[float]] = {}
        if can_project and at is not None:
            for name in get_args(ScenarioId):
                endpoints[name] = _projected(entity, name, ahead, at, decay, exposure, known)
        projection = (
            [
                TrendComparePoint(
                    day=last + timedelta(days=n),
                    value=scale(entity, endpoints[scenario][i]),
                )
                for i, n in enumerate(ahead)
            ]
            if endpoints
            else []
        )
        lines.append(
            TrendCompareLine(
                entity=entity.key,
                kind=entity.kind,
                entity_id=entity.entity_id,
                label=entity.label,
                points=[TrendComparePoint(day=days[i], value=scale(entity, raw[i])) for i in keep],
                start_value=known_values[0] if known_values else None,
                end_value=known_values[-1] if known_values else None,
                change=change(known_values),
                moderate_end=scale(entity, endpoints["moderate"][-1]) if endpoints else None,
                fast_end=scale(entity, endpoints["fast"][-1]) if endpoints else None,
                projection=projection,
            )
        )
    bls = pipeline.bls_retrieval() if can_project else None
    return TrendCompareResponse(
        kind=kind,
        start=start,
        end=end,
        window_days=WINDOW,
        step_days=1 if len(days) <= DAILY_POINTS_UP_TO else WEEKLY_STEP,
        available_from=available_from,
        available_to=newest,
        mode=shown,
        raw_fallback=mode == "indexed" and shown == "raw",
        base_date=days[base_at] if base_at is not None else None,
        horizon_days=horizon,
        projected_from=last if can_project else None,
        projected_to=last + timedelta(days=horizon) if can_project else None,
        lines=lines,
        options=options,
        meta=meta(plotted),
        projection_meta=RecommendationMeta(
            sources=[
                source,
                Source(
                    name="BLS Occupational Projections 2023-2033 (static baseline)",
                    url=pipeline.BLS_URL,
                    retrieved_at=date.fromisoformat(bls["retrieved_at"] if bls else ""),
                ),
            ],
            snapshot_date=last,
            scenario=scenario,
            is_estimate=True,
            observed_from=prior - timedelta(days=WINDOW - 1),
            observed_to=last,
        )
        if can_project
        else None,
    )


def rolling_window_shares(
    prior: date,
    last: date,
    papers: Mapping[date, int],
    mentions: Mapping[tuple[date, str], int],
    skill_ids: Sequence[str],
) -> dict[str, tuple[float, float]] | None:
    """Per skill, the shares of the previous and last 7-day windows; None if either is partial."""
    out: dict[str, tuple[float, float]] = {}
    for sid in skill_ids:
        before, current = rolling_shares([prior, last], papers, mentions, sid)
        if before is None or current is None:
            return None
        out[sid] = (before, current)
    return out


def _projected(
    entity: Entity,
    scenario: ScenarioId,
    ahead: Sequence[int],
    at: Mapping[str, tuple[float, float]],
    decay: Mapping[str, tuple[float, str]],
    exposure: Mapping[str, float],
    known: Mapping[str, Entity],
) -> list[float]:
    """Project each skill with its own velocity, then combine exactly like the observed line."""

    def skill(sid: str) -> list[float]:
        before, current = at[sid]
        velocity = scenario_velocities(
            before,
            current,
            decay.get(sid, (0.0, ""))[0],
            exposure.get(sid, NEUTRAL_EXPOSURE),
        )[scenario]
        return [project(current, velocity, n) for n in ahead]

    def role(role_entity: Entity) -> list[float]:
        weights = dict(role_entity.skills)
        total = sum(weights.values())
        lines = {sid: skill(sid) for sid in weights}
        return [sum(lines[s][i] * w for s, w in weights.items()) / total for i in range(len(ahead))]

    if entity.kind == "skill":
        return skill(entity.entity_id)
    if entity.kind == "role":
        return role(entity)
    roles = [role(known[f"role:{r}"]) for r in entity.roles]
    return [sum(r[i] for r in roles) / len(roles) for i in range(len(ahead))]
