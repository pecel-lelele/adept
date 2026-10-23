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
from app.core.errors import NotFoundError
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
    and anything served from the frozen fixture (database down) for FALLBACK_TTL_S so recovery
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
        snap = repository.get_snapshot(ctx, snapshot_date, scenario, strict=strict)
        from_db = ctx.source == "db"
    finally:
        ctx.close()
    ttl = FALLBACK_TTL_S if not from_db else LATEST_TTL_S if snapshot_date is None else DATED_TTL_S
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[key] = (now + ttl, snap)
    return snap


LATEST_TTL_S = 60.0
DATED_TTL_S = 600.0
FALLBACK_TTL_S = 5.0
_CACHE_MAX = 64
_cache_lock = threading.Lock()
_cache: dict[tuple[date | None, str, bool], tuple[float, TrendSnapshotResponse]] = {}


def clear_cache() -> None:
    """Forget cached snapshots (after a pipeline publish, and between tests)."""
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# Radar / entity signals (legacy contract), derived from the latest snapshot
# ---------------------------------------------------------------------------

DIRECTION_BAND = 0.05  # same band as the pipeline's direction(v)


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
        covered = [r for r in pathway_data.requirements(role_id) if r.skill_id in by_skill]
        weight = sum(r.importance for r in covered)
        if weight <= 0:
            continue
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
            )
        )
    return out


def get_radar(scenario: ScenarioId) -> RadarResponse:
    snap = get_snapshot(None, scenario)
    return RadarResponse(items=signals_from_snapshot(snap, scenario), meta=_meta(snap, scenario))


def get_role_trend(entity_id: str, scenario: ScenarioId) -> RoleTrendResponse:
    snap = get_snapshot(None, scenario)
    signal = next(
        (s for s in signals_from_snapshot(snap, scenario) if s.entity_id == entity_id), None
    )
    if signal is None:
        raise NotFoundError(f"No trend signal for {entity_id}")
    return RoleTrendResponse(signal=signal, meta=_meta(snap, scenario))
