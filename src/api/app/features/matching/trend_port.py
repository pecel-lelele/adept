"""Thin adapter: fetches M1''s trend snapshot and returns a TrendSnapshot value object.

Design:
- All calls go to M1''s trends service IN-PROCESS (no HTTP self-call).
  FastAPI already runs the sync handler on a thread-pool thread; calling ourselves
  over HTTP would hold two pool threads per request and starve the pool under load.
- The trends service may call psycopg.connect(), which can block indefinitely on a
  hung or slow DB.  We wrap the call on a daemon thread and join with SNAPSHOT_TIMEOUT_S,
  matching M3''s pathway port pattern (``_call_with_timeout`` in pathway/trend_port.py).
- On any failure or timeout, raise TrendUnavailable -> 503.  Never swallow errors
  or invent a date/source.

In tests: patch ``fetch_snapshot`` in ``app.features.matching.service`` to inject a
fake without touching the real trends module.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date

from app.contracts.common import ScenarioId, Source
from app.core.errors import TrendUnavailableError

# Public alias so tests import from one place.
TrendUnavailable = TrendUnavailableError

# How long (seconds) to wait for M1''s snapshot before declaring it unavailable.
# Mirrors M1_TIMEOUT_S in pathway/trend_port.py (both guard the same psycopg call).
SNAPSHOT_TIMEOUT_S: float = 2.0


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


def fetch_snapshot(scenario: ScenarioId) -> TrendSnapshot:
    """Return a ``TrendSnapshot`` from M1's trends service with a bounded wait.

    Raises ``TrendUnavailable`` if:
    - the call takes longer than SNAPSHOT_TIMEOUT_S (hung DB connect)
    - M1's service raises any exception
    - the snapshot contains no items or no source attribution
    """
    snap = _call_with_timeout(scenario)  # raises TrendUnavailable on any failure

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
    )


def _call_with_timeout(scenario: ScenarioId):  # type: ignore[return]
    """Call M1''s get_snapshot on a daemon thread with a bounded join.

    A hung psycopg.connect() will neither block the request past SNAPSHOT_TIMEOUT_S
    nor prevent the process from exiting (daemon=True).

    Mirrors ``_call_with_timeout`` in pathway/trend_port.py.
    """
    from app.features.trends import service as trends_service

    box: dict[str, object] = {}

    def _run() -> None:
        try:
            box["value"] = trends_service.get_snapshot(snapshot_date=None, scenario=scenario)
        except BaseException as exc:  # noqa: BLE001 - re-raised below in the caller thread
            box["error"] = exc

    worker = threading.Thread(target=_run, name="matching-m1-trends", daemon=True)
    worker.start()
    worker.join(SNAPSHOT_TIMEOUT_S)

    if worker.is_alive():
        raise TrendUnavailable(
            f"Trend snapshot for scenario {scenario!r} timed out "
            f"after {SNAPSHOT_TIMEOUT_S:g}s — M1 service may be unavailable."
        )
    if "error" in box:
        exc = box["error"]
        raise TrendUnavailable(
            f"Trend snapshot unavailable for scenario {scenario!r}: {exc}"
        ) from exc  # type: ignore[misc]

    return box["value"]
