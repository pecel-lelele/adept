"""Trend input for the pathway (F5), read from M1's AI-trend signal layer (F2/F3).

One place decides which trend data the pathway, re-plan, SDG contribution and the About page see:

1. M1's snapshot (`trends.service.get_snapshot`, in process, no HTTP self-call). Its
   `velocity_<scenario>` already models the scenario, so the engine must not weight it again
   (`scenario_weighted=True`).
2. Fallback: M1's shared last good database snapshot or committed fixture, with its actual
   date, sources and is_fallback flag. These velocities also already model the scenario.

Skills that M1 does not score (e.g. excel, rpa, sql today) get no signal: the engine treats them
as neutral and the pathway lists them in a warning instead of inventing a value.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date

from app.contracts.common import ScenarioId, Source
from app.contracts.trends import TrendSnapshotResponse
from app.core.errors import NotFoundError
from app.features.pathway import data
from app.features.trends import service as trends_service

log = logging.getLogger(__name__)

M1_PREFIX = "m1-"
CACHE_TTL_S = 30.0
# F2 owns operation-level I/O deadlines; retry after its central fallback TTL.
M1_RETRY_AFTER_S = trends_service.FALLBACK_TTL_S


@dataclass(frozen=True)
class TrendView:
    snapshot: data.Snapshot
    growth: dict[str, float]  # skill_id -> demand signal for the requested scenario
    scenario_weighted: bool  # True when the source already models the scenario
    available_dates: tuple[date, ...] = ()
    provenance_note: str = ""

    @property
    def is_m1(self) -> bool:
        return self.snapshot.version.startswith(M1_PREFIX)

    def uncovered(self, skill_ids: list[str]) -> list[str]:
        return [s for s in skill_ids if s not in self.growth]


_cache: dict[tuple[ScenarioId, date | None], tuple[float, TrendView | None]] = {}
_m1_down_until = 0.0


def reset_cache() -> None:
    global _m1_down_until
    _cache.clear()
    _m1_down_until = 0.0


def current(scenario: ScenarioId, snapshot_date: date | None = None) -> TrendView | None:
    """Trend view for `scenario`: the latest snapshot, or `snapshot_date` to replay an older one."""
    key = (scenario, snapshot_date)
    hit = _cache.get(key)
    ttl = (
        trends_service.FALLBACK_TTL_S
        if hit and hit[1] and hit[1].snapshot.is_fallback
        else CACHE_TTL_S
    )
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    view = _from_m1(scenario, snapshot_date)
    _cache[key] = (time.monotonic(), view)
    return view


def latest_version() -> str:
    """Version string of the latest snapshot; a change means the saved plan may need a re-plan."""
    view = current("moderate")
    return view.snapshot.version if view else ""


def _from_m1(scenario: ScenarioId, snapshot_date: date | None) -> TrendView | None:
    global _m1_down_until
    try:
        snap = (
            trends_service.last_good_snapshot(snapshot_date, scenario)
            if time.monotonic() < _m1_down_until
            else _read_snapshot(scenario, snapshot_date)
        )
    except NotFoundError:
        return None  # M1 is up but has no snapshot for that date
    except Exception:  # noqa: BLE001 - serving fallback is shared with radar and matching
        _m1_down_until = time.monotonic() + M1_RETRY_AFTER_S
        log.warning("Trend snapshot unavailable; serving the shared last good snapshot")
        try:
            snap = trends_service.last_good_snapshot(snapshot_date, scenario)
        except NotFoundError:
            return None
    if not snap.items or not snap.meta.sources:
        return None
    sources = tuple(
        Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
    )
    day = snap.meta.snapshot_date
    key = f"velocity_{scenario}"
    return TrendView(
        snapshot=data.Snapshot(
            id=f"{M1_PREFIX}{day.isoformat()}",
            version=f"{M1_PREFIX}{day.isoformat()}",
            source=sources[0],
            sources=sources,
            snapshot_date=day,
            served_from=snap.meta.served_from,
            is_fallback=snap.meta.is_fallback,
        ),
        growth={item.skill_id: float(getattr(item, key)) for item in snap.items},
        scenario_weighted=True,
        available_dates=tuple(snap.meta.available_snapshots),
        provenance_note=snap.meta.data_provenance_note or "",
    )


def _read_snapshot(scenario: ScenarioId, snapshot_date: date | None) -> TrendSnapshotResponse:
    """F2 bounds connect/query/socket I/O and closes it on this request's own thread.

    No waiting-only timeout or abandoned worker is introduced by the pathway adapter.
    F2's negative cache and this adapter's backoff suppress repeated outage reads.
    """
    return trends_service.get_snapshot(snapshot_date, scenario)
