"""Thin adapter: fetches M1''s trend snapshot and returns a TrendSnapshot value object.

Design:
- All calls go to M1''s trends service IN-PROCESS (no HTTP self-call).
  FastAPI already runs the sync handler on a thread-pool thread; calling ourselves
  over HTTP would hold two pool threads per request and starve the pool under load.
- The trends service may call psycopg.connect(), which can block indefinitely on a
  hung or slow DB. We wait on a daemon worker for SNAPSHOT_TIMEOUT_S and allow only
  one outstanding worker, even after a request times out.
- On any failure or timeout, raise TrendUnavailable -> 503.  Never swallow errors
  or invent a date/source.
- Demo mode uses M1's documented fixture fallback. Other auth modes require a
  database snapshot, so an unavailable M1 source returns 503.

In tests: patch ``fetch_snapshot`` in ``app.features.matching.service`` to inject a
fake without touching the real trends module.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date

from app.contracts.common import ScenarioId, Source
from app.contracts.trends import TrendSnapshotResponse
from app.core.config import get_settings
from app.core.errors import NotFoundError, TrendUnavailableError

# Public alias so tests import from one place.
TrendUnavailable = TrendUnavailableError

# How long (seconds) to wait for M1''s snapshot before declaring it unavailable.
# Mirrors M1_TIMEOUT_S in pathway/trend_port.py (both guard the same psycopg call).
# A timed-out DB call holds the sole worker slot until it actually returns.
SNAPSHOT_TIMEOUT_S: float = 2.0
_WORKER_SLOT = threading.BoundedSemaphore(value=1)
_IN_FLIGHT_LOCK = threading.Lock()


@dataclass
class _SnapshotCall:
    done: threading.Event
    scenario: ScenarioId
    snapshot_date: date | None
    strict: bool
    value: TrendSnapshotResponse | None = None
    error: BaseException | None = None
    timed_out: bool = False


_IN_FLIGHT: _SnapshotCall | None = None


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
    )


def _call_with_timeout(
    scenario: ScenarioId, snapshot_date: date | None = None
) -> TrendSnapshotResponse:
    """Share one bounded getter across concurrent requests.

    Concurrent requests wait on the same snapshot. A timed-out thread holds the
    worker slot until it exits; later requests fail fast while it remains stuck.
    """
    from app.features.trends import service as trends_service

    global _IN_FLIGHT
    strict = get_settings().auth_mode != "demo"
    with _IN_FLIGHT_LOCK:
        call = _IN_FLIGHT
        if call is not None and call.timed_out:
            raise TrendUnavailable(
                "Trend snapshot unavailable because the previous database read is still running."
            )
        if call is not None and (
            call.scenario != scenario
            or call.snapshot_date != snapshot_date
            or call.strict != strict
        ):
            raise TrendUnavailable("A different trend snapshot read is still running.")
        if call is None:
            if not _WORKER_SLOT.acquire(blocking=False):
                raise TrendUnavailable(
                    "Trend snapshot unavailable because the previous database read "
                    "is still running."
                )
            call = _SnapshotCall(
                done=threading.Event(),
                scenario=scenario,
                snapshot_date=snapshot_date,
                strict=strict,
            )
            _IN_FLIGHT = call

            def _run() -> None:
                global _IN_FLIGHT
                try:
                    from app.features.trends.repository import TrendsUnavailableError
                except ImportError as exc:
                    call.error = exc
                else:
                    try:
                        if strict:
                            call.value = trends_service.get_snapshot(
                                snapshot_date=snapshot_date, scenario=scenario, strict=True
                            )
                        else:
                            call.value = trends_service.get_snapshot(
                                snapshot_date=snapshot_date, scenario=scenario
                            )
                    except TrendsUnavailableError as exc:
                        call.error = exc
                    except BaseException as exc:  # noqa: BLE001 - re-raised in caller thread
                        call.error = exc
                finally:
                    with _IN_FLIGHT_LOCK:
                        _WORKER_SLOT.release()
                        if _IN_FLIGHT is call:
                            _IN_FLIGHT = None
                    call.done.set()

            worker = threading.Thread(target=_run, name="matching-m1-trends", daemon=True)
            try:
                worker.start()
            except RuntimeError:
                _WORKER_SLOT.release()
                _IN_FLIGHT = None
                raise

    if not call.done.wait(SNAPSHOT_TIMEOUT_S):
        with _IN_FLIGHT_LOCK:
            if not call.done.is_set() and _IN_FLIGHT is call:
                call.timed_out = True
        if not call.done.is_set():
            raise TrendUnavailable(
                f"Trend snapshot for scenario {scenario!r} timed out "
                f"after {SNAPSHOT_TIMEOUT_S:g}s — M1 service may be unavailable."
            )

    if call.error is not None:
        exc = call.error
        if isinstance(exc, NotFoundError):
            raise exc
        raise TrendUnavailable(
            f"Trend snapshot unavailable for scenario {scenario!r}: {exc}"
        ) from exc
    if call.value is None:
        raise TrendUnavailable("Trend service returned no snapshot.")
    return call.value
