"""Trend snapshot service (F2 + F3 owner: M1).

Business logic layer between the router and the repository.
Also keeps the legacy get_radar / get_role_trend functions alive so that
existing tests and the frontend's legacy endpoints continue to work unchanged.
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.trends import (
    RadarResponse,
    RoleTrendResponse,
    TrendSnapshotResponse,
)
from app.core.errors import NotFoundError
from app.features.trends import repository

# ---------------------------------------------------------------------------
# New snapshot endpoint (F2 final contract)
# ---------------------------------------------------------------------------


def get_snapshot(snapshot_date: date | None, scenario: ScenarioId) -> TrendSnapshotResponse:
    """Return the trend snapshot for the given date and scenario.

    If snapshot_date is None, returns the latest available snapshot.
    meta.available_snapshots lists every stored date for the frontend
    trend-replay toggle.
    """
    ctx = repository.resolve_context()
    try:
        return repository.get_snapshot(ctx, snapshot_date, scenario)
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# Legacy endpoints (kept for backward compat with existing skeleton tests)
# ---------------------------------------------------------------------------


def get_radar(scenario: ScenarioId) -> RadarResponse:
    return RadarResponse(items=repository.list_signals(scenario), meta=mock_meta(scenario))


def get_role_trend(role_id: str, scenario: ScenarioId) -> RoleTrendResponse:
    signal = repository.get_signal(None, role_id, scenario)
    if signal is None:
        raise NotFoundError(f"No trend signal for role {role_id}")
    return RoleTrendResponse(signal=signal, meta=mock_meta(scenario))
