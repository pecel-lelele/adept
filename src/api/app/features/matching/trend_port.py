"""Thin adapter: fetches M1's trend snapshot and returns a TrendSnapshot value object.

Design:
- All calls go to M1's trends service IN-PROCESS (no HTTP self-call).
- M1's service caches published snapshots, so most calls return immediately.
- A cache miss reads PostgreSQL on a small shared thread pool and is bounded by
  SNAPSHOT_TIMEOUT_S, so a slow database cannot hold a request open. Different users and
  scenarios read in parallel (an earlier single-worker lock queued every request behind one).
- On a read failure or timeout, use M1's shared disclosed last good snapshot.
  Explicit unknown dates and malformed snapshots remain errors; never invent a date/source.

In tests: patch ``fetch_snapshot`` in ``app.features.matching.service`` to inject a
fake without touching the real trends module.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import date

from app.contracts.common import ScenarioId, Source
from app.contracts.trends import TrendSnapshotResponse
from app.core.config import get_settings
from app.core.errors import NotFoundError, TrendUnavailableError
from app.features.trends.repository import SourceType

# Public alias so tests import from one place.
TrendUnavailable = TrendUnavailableError

# How long (seconds) to wait for an uncached snapshot before declaring it unavailable.
SNAPSHOT_TIMEOUT_S: float = 2.0
# Shared by every request; threads are created on demand and reused.
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="matching-m1-trends")
# Reads that may be queued or running at once. Beyond this, callers get 503 at once instead of
# queueing work that would outlive their request (a slow database cannot grow the queue).
MAX_OUTSTANDING = 16
_slots = threading.BoundedSemaphore(MAX_OUTSTANDING)
# Concurrent requests for the same snapshot share one read.
_inflight: dict[tuple[date | None, str, bool], Future[TrendSnapshotResponse]] = {}
_inflight_lock = threading.Lock()
# After a failed or timed-out read, answer from the shared last good snapshot until this
# monotonic time instead of paying SNAPSHOT_TIMEOUT_S on every request during an outage.
# Only non-strict (development) reads use this shortcut: strict/production reads never record
# or honour it, so each request re-attempts the authoritative database read.
RETRY_AFTER_S: float = 5.0
_down_until = 0.0


def reset_down() -> None:
    """Forget a recorded outage (after a trend refresh, and between tests)."""
    global _down_until
    _down_until = 0.0


def _mark_down() -> None:
    global _down_until
    _down_until = time.monotonic() + RETRY_AFTER_S


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
    served_from: SourceType = "db"
    is_fallback: bool = False
    reference_velocities: dict[str, float] | None = None
    available_snapshots: list[date] = field(default_factory=list)


def fetch_snapshot(scenario: ScenarioId, snapshot_date: date | None = None) -> TrendSnapshot:
    """Return a ``TrendSnapshot`` from M1's trends service with a bounded wait.

    Read failures and bounded waits use the central last good snapshot. Empty snapshots or
    missing attribution still raise ``TrendUnavailable``; unknown replay dates stay 404.
    """
    try:
        snap = _call_with_timeout(scenario, snapshot_date)
    except TrendUnavailable:
        from app.features.trends import service as trends_service

        snap = trends_service.last_good_snapshot(snapshot_date, scenario, outage=True)

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
        served_from=snap.meta.served_from,
        is_fallback=snap.meta.is_fallback,
        available_snapshots=list(snap.meta.available_snapshots),
        reference_velocities={
            item.skill_id: float(
                getattr(item, "velocity_fast" if scenario == "moderate" else "velocity_moderate")
            )
            for item in snap.items
        },
    )


def _start_read(
    key: tuple[date | None, str, bool], scenario: ScenarioId, snapshot_date: date | None
) -> Future[TrendSnapshotResponse]:
    """The running read for `key`, or a new one if a slot is free (else TrendUnavailable)."""
    from app.features.trends import service as trends_service

    with _inflight_lock:
        running = _inflight.get(key)
        if running is not None and not running.done():
            return running
        slots = _slots  # release the same semaphore that was acquired
        if not slots.acquire(blocking=False):
            raise TrendUnavailable("Trend reads are backed up; please retry in a moment.")
        kwargs: dict[str, object] = {"snapshot_date": snapshot_date, "scenario": scenario}
        if key[2]:
            kwargs["strict"] = True
        future = _EXECUTOR.submit(trends_service.get_snapshot, **kwargs)
        _inflight[key] = future

    def finished(done: Future[TrendSnapshotResponse]) -> None:
        slots.release()
        with _inflight_lock:
            if _inflight.get(key) is done:
                del _inflight[key]

    future.add_done_callback(finished)
    return future


def _call_with_timeout(
    scenario: ScenarioId, snapshot_date: date | None = None
) -> TrendSnapshotResponse:
    """Read M1's snapshot, giving up after SNAPSHOT_TIMEOUT_S.

    A caller that times out stops sharing that read, so the next caller starts a fresh one; the
    slow read still holds its slot until it ends (bounded by MAX_OUTSTANDING).
    """
    strict = get_settings().app_env == "production"
    if not strict and time.monotonic() < _down_until:
        raise TrendUnavailable("Trend snapshot recently unavailable; retrying shortly.")
    key = (snapshot_date, scenario, strict)
    future = _start_read(key, scenario, snapshot_date)
    try:
        value = future.result(timeout=SNAPSHOT_TIMEOUT_S)
    except FuturesTimeout as exc:
        with _inflight_lock:
            if _inflight.get(key) is future:
                del _inflight[key]
        future.cancel()  # only succeeds if it has not started yet
        if not strict:
            _mark_down()
        raise TrendUnavailable(
            f"Trend snapshot for scenario {scenario!r} timed out "
            f"after {SNAPSHOT_TIMEOUT_S:g}s — M1 service may be unavailable."
        ) from exc
    except NotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001 - every M1 failure is a 503 for matching
        if not strict:
            _mark_down()
        raise TrendUnavailable(
            f"Trend snapshot unavailable for scenario {scenario!r}: {exc}"
        ) from exc
    if value is None:
        raise TrendUnavailable("Trend service returned no snapshot.")
    return value
