"""Trend snapshot service (F2 + F3 owner: M1).

Business logic layer between the router and the repository.
Also keeps the legacy get_radar / get_role_trend functions alive so that
existing tests and the frontend's legacy endpoints continue to work unchanged.
"""

from __future__ import annotations

import threading
import time
from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.trends import (
    Direction,
    RadarResponse,
    RoleTrendResponse,
    TrendSignal,
    TrendSnapshotResponse,
)
from app.core.errors import NotFoundError, TrendUnavailableError
from app.features.trends import repository

# ---------------------------------------------------------------------------
# New snapshot endpoint (F2 final contract)
# ---------------------------------------------------------------------------


def get_snapshot(
    snapshot_date: date | None, scenario: ScenarioId, strict: bool = False
) -> TrendSnapshotResponse:
    """Return the trend snapshot for the given date and scenario.

    If snapshot_date is None, returns the latest available snapshot.
    meta.available_snapshots lists every stored date for the frontend
    trend-replay toggle.

    strict=True requires database data and raises repository.TrendsUnavailableError
    on database failure or an empty database. An unknown requested date remains
    NotFoundError. HTTP callers retain the default demo fallback behavior.

    Published snapshots never change, so results are cached in process: a dated snapshot for
    DATED_TTL_S, "latest" for LATEST_TTL_S (a new weekly snapshot shows up within a minute),
    and any disclosed fallback for FALLBACK_TTL_S so recovery
    is quick. Without this every radar, matches, plan and outlook view re-read ~110 rows.
    """
    key = (snapshot_date, scenario, strict)
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
    if hit is not None and now < hit[0]:
        return hit[1]
    ctx = repository.resolve_context(strict=strict)
    try:
        if ctx.source == "fixture" and not strict:
            snap = last_good_snapshot(snapshot_date, scenario, outage=ctx.outage)
        else:
            try:
                snap = repository.get_snapshot(ctx, snapshot_date, scenario, strict=strict)
            except NotFoundError:
                if strict or (
                    snapshot_date is not None and snapshot_date not in ctx.available_dates
                ):
                    raise
                snap = last_good_snapshot(snapshot_date, scenario)
    finally:
        ctx.close()
    from_db = snap.meta.served_from == "db" and not snap.meta.is_fallback
    ttl = FALLBACK_TTL_S if not from_db else LATEST_TTL_S if snapshot_date is None else DATED_TTL_S
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[key] = (now + ttl, snap)
        if from_db:
            _last_good[snap.meta.snapshot_date] = snap
            if len(_last_good) > _CACHE_MAX:
                del _last_good[min(_last_good)]
    return snap


LATEST_TTL_S = 60.0
DATED_TTL_S = 600.0
FALLBACK_TTL_S = 5.0
_CACHE_MAX = 64
_cache_lock = threading.Lock()
_cache: dict[tuple[date | None, str, bool], tuple[float, TrendSnapshotResponse]] = {}
_last_good: dict[date, TrendSnapshotResponse] = {}


def last_good_snapshot(
    snapshot_date: date | None, scenario: ScenarioId, *, outage: bool = False
) -> TrendSnapshotResponse:
    """One non-I/O serving fallback; never substitute another date for a replay request.

    ``outage=True`` means the database could not be read: a replay date we hold no copy of
    may well exist there, so it is unavailable (503), not unknown (404).
    """
    from app.features.trends import mocks

    with _cache_lock:
        available = sorted(set(_last_good) | set(mocks.AVAILABLE_MOCK_DATES))
        snap = (
            _last_good.get(snapshot_date)
            if snapshot_date is not None
            else max(
                _last_good.values(),
                key=lambda value: value.meta.snapshot_date,
                default=None,
            )
        )
    if snap is None:
        if snapshot_date is not None and snapshot_date not in mocks.AVAILABLE_MOCK_DATES:
            if outage:
                raise TrendUnavailableError(
                    f"Trend data for {snapshot_date.isoformat()} is unavailable right now; "
                    "the trend database could not be read."
                )
            raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")
        snap = mocks.snapshot(scenario, snapshot_date)
    return snap.model_copy(
        update={
            "meta": snap.meta.model_copy(
                update={"scenario": scenario, "is_fallback": True, "available_snapshots": available}
            )
        },
        deep=True,
    )


def clear_cache() -> None:
    """Forget cached snapshots (after a pipeline publish, and between tests)."""
    with _cache_lock:
        _cache.clear()
        _last_good.clear()


# ---------------------------------------------------------------------------
# Radar / entity signals (legacy contract), derived from the latest snapshot
# ---------------------------------------------------------------------------

DIRECTION_BAND = 0.05  # same band as the pipeline's direction(v)
# Below this share of a role's skill importance with trend data, its direction is shown as
# "insufficient evidence" rather than as rising or declining.
MIN_ROLE_COVERAGE = 0.5


def _direction(v: float) -> Direction:
    if v > DIRECTION_BAND:
        return "rising"
    if v < -DIRECTION_BAND:
        return "declining"
    return "stable"


def _meta(snap: TrendSnapshotResponse, scenario: ScenarioId) -> RecommendationMeta:
    return RecommendationMeta(
        sources=[
            Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
        ],
        snapshot_date=snap.meta.snapshot_date,
        scenario=scenario,
        is_estimate=True,
        served_from=snap.meta.served_from,
        is_fallback=snap.meta.is_fallback,
        observed_from=snap.meta.observed_from,
        observed_to=snap.meta.observed_to,
    )


def signals_from_snapshot(snap: TrendSnapshotResponse, scenario: ScenarioId) -> list[TrendSignal]:
    """One signal per tracked skill plus one per target role (importance-weighted over the
    role's covered skills). Exposure is the pipeline's automation_exposure; the rest of a
    skill's work is counted as augmentation."""
    from app.features.pathway import data as pathway_data

    velocity_key, direction_key = f"velocity_{scenario}", f"direction_{scenario}"
    by_skill = {i.skill_id: i for i in snap.items}
    out = [
        TrendSignal(
            entity_type="skill",
            entity_id=i.skill_id,
            label=i.skill_label,
            direction=getattr(i, direction_key),
            growth_rate=round(float(getattr(i, velocity_key)), 4),
            ai_exposure=i.automation_exposure,
            automation_share=i.automation_exposure,
            augmentation_share=round(1.0 - i.automation_exposure, 4),
        )
        for i in snap.items
    ]
    labels = pathway_data.role_labels()
    for role_id in pathway_data.target_role_ids():
        requirements = pathway_data.requirements(role_id)
        covered = [r for r in requirements if r.skill_id in by_skill]
        weight = sum(r.importance for r in covered)
        total = sum(r.importance for r in requirements)
        if weight <= 0 or total <= 0:
            continue
        coverage = min(1.0, weight / total)
        growth = sum(r.importance * getattr(by_skill[r.skill_id], velocity_key) for r in covered)
        exposure = sum(r.importance * by_skill[r.skill_id].automation_exposure for r in covered)
        growth, exposure = growth / weight, min(1.0, max(0.0, exposure / weight))
        out.append(
            TrendSignal(
                entity_type="role",
                entity_id=role_id,
                label=labels.get(role_id, role_id),
                direction=_direction(growth),
                growth_rate=round(growth, 4),
                ai_exposure=round(exposure, 4),
                automation_share=round(exposure, 4),
                augmentation_share=round(1.0 - exposure, 4),
                trend_coverage=round(coverage, 4),
                insufficient_evidence=coverage < MIN_ROLE_COVERAGE,
            )
        )
    return out


def get_radar(scenario: ScenarioId, snapshot_date: date | None = None) -> RadarResponse:
    snap = get_snapshot(snapshot_date, scenario)
    return RadarResponse(items=signals_from_snapshot(snap, scenario), meta=_meta(snap, scenario))


def get_role_trend(entity_id: str, scenario: ScenarioId) -> RoleTrendResponse:
    snap = get_snapshot(None, scenario)
    signal = next(
        (s for s in signals_from_snapshot(snap, scenario) if s.entity_id == entity_id), None
    )
    if signal is None:
        raise NotFoundError(f"No trend signal for {entity_id}")
    return RoleTrendResponse(signal=signal, meta=_meta(snap, scenario))
