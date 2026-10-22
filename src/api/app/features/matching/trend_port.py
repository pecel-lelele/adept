"""Thin adapter: fetches M1's trend snapshot and returns a TrendSnapshot value object.

Design:
- All calls go to M1's trends service IN-PROCESS (no HTTP self-call).
- M1's service caches published snapshots, so most calls return immediately.
- A cache miss reads PostgreSQL on a small shared thread pool and is bounded by
  SNAPSHOT_TIMEOUT_S, so a slow database cannot hold a request open. Different users and
  scenarios read in parallel (an earlier single-worker lock queued every request behind one).
- On any failure or timeout, raise TrendUnavailable -> 503. Never swallow errors
  or invent a date/source.
- Demo mode uses M1's documented fixture fallback. Other auth modes require a
  database snapshot, so an unavailable M1 source returns 503.

In tests: patch ``fetch_snapshot`` in ``app.features.matching.service`` to inject a
fake without touching the real trends module.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from datetime import date

from app.contracts.common import ScenarioId, Source
from app.contracts.trends import TrendSnapshotResponse
from app.core.config import get_settings
from app.core.errors import NotFoundError, TrendUnavailableError

# Public alias so tests import from one place.
TrendUnavailable = TrendUnavailableError

# How long (seconds) to wait for an uncached snapshot before declaring it unavailable.
SNAPSHOT_TIMEOUT_S: float = 2.0
# Shared by every request; threads are created on demand and reused.
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="matching-m1-trends")


@dataclass(frozen=True)
class TrendSnapshot:
    """All trend data needed by the matching service.

    Every field comes directly from the snapshot''s ``meta``; nothing is invented.
    """

    velocities: dict[str, float]  # skill_id -> velocity for the requested scenario
    snapshot_date: date  # from meta.snapshot_date
    sources: list[Source]  # from meta.sources, converted to common.Source
    scenario: ScenarioId  # the requested scenario
    is_estimate: bool  # from meta.is_estimate
    data_provenance_note: str | None = None  # preserve M1's historical/fixture disclosure
    observed_from: date | None = None  # period the source data measures (H09)
    observed_to: date | None = None


def fetch_snapshot(scenario: ScenarioId, snapshot_date: date | None = None) -> TrendSnapshot:
    """Return a ``TrendSnapshot`` from M1's trends service with a bounded wait.

    Raises ``TrendUnavailable`` if:
    - the call takes longer than SNAPSHOT_TIMEOUT_S (hung DB connect)
    - M1's service raises any exception
    - the snapshot contains no items or no source attribution
    """
    snap = _call_with_timeout(scenario, snapshot_date)

    if snap.meta.scenario != scenario or (
        snapshot_date is not None and snap.meta.snapshot_date != snapshot_date
    ):
        raise TrendUnavailable("Trend service returned a snapshot for a different request.")

    if not snap.items:
        raise TrendUnavailable(f"Trend snapshot for scenario {scenario!r} returned no skill items.")
    if not snap.meta.sources:
        raise TrendUnavailable(
            f"Trend snapshot for scenario {scenario!r} carries no source attribution."
        )

    velocity_key = f"velocity_{scenario}"
    velocities = {
        item.skill_id: float(getattr(item, velocity_key))
        for item in snap.items
        if hasattr(item, velocity_key)
    }

    sources = [
        Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
    ]

    return TrendSnapshot(
        velocities=velocities,
        snapshot_date=snap.meta.snapshot_date,
        sources=sources,
        scenario=scenario,
        is_estimate=snap.meta.is_estimate,
        data_provenance_note=snap.meta.data_provenance_note,
        observed_from=snap.meta.observed_from,
        observed_to=snap.meta.observed_to,
    )


def _call_with_timeout(
    scenario: ScenarioId, snapshot_date: date | None = None
) -> TrendSnapshotResponse:
    """Read M1's snapshot, giving up after SNAPSHOT_TIMEOUT_S."""
    from app.features.trends import service as trends_service

    strict = get_settings().auth_mode != "demo"
    kwargs: dict[str, object] = {"snapshot_date": snapshot_date, "scenario": scenario}
    if strict:
        kwargs["strict"] = True
    future = _EXECUTOR.submit(trends_service.get_snapshot, **kwargs)
    try:
        value = future.result(timeout=SNAPSHOT_TIMEOUT_S)
    except FuturesTimeout as exc:
        raise TrendUnavailable(
            f"Trend snapshot for scenario {scenario!r} timed out "
            f"after {SNAPSHOT_TIMEOUT_S:g}s — M1 service may be unavailable."
        ) from exc
    except NotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001 - every M1 failure is a 503 for matching
        raise TrendUnavailable(
            f"Trend snapshot unavailable for scenario {scenario!r}: {exc}"
        ) from exc
    if value is None:
        raise TrendUnavailable("Trend service returned no snapshot.")
    return value
