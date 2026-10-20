"""Matching service (F4).

Bridges the HTTP layer → scoring engine.  Fetches the latest velocity
snapshot from M1's trend endpoint (or uses an empty dict → NEUTRAL fallback),
then delegates to ``repository`` which runs ``scoring.rank_roles``.
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.matching import MatchResponse, RoleMatch
from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.features.matching import repository
from app.features.matching.trend_port import fetch_velocities

# Self-call base URL: the FastAPI server runs on the same process; using
# localhost avoids cross-service latency and keeps the demo stack simple.
_API_BASE = "http://127.0.0.1:8000"

_TREND_SOURCE = "http://127.0.0.1:8000/api/v1/trends/snapshot"


def _velocities(scenario: ScenarioId) -> tuple[dict[str, float], date]:
    """Fetch skill velocities from M1's trend snapshot endpoint.

    Falls back to an empty dict (→ NEUTRAL for every skill) if the trends
    service is unavailable or returns an error.
    Returns ``(velocities, snapshot_date)`` where snapshot_date defaults
    to today on fallback.
    """
    settings = get_settings()
    base = getattr(settings, "api_base_url", None) or _API_BASE
    vels = fetch_velocities(base, scenario)
    snap_date = date.today()
    return vels, snap_date


def list_matches(user: CurrentUser, scenario: ScenarioId) -> MatchResponse:
    vels, snap_date = _velocities(scenario)
    matches = repository.list_matches(user.id, scenario, vels, snap_date)
    # Top-level meta mirrors what the best match carries; if list is empty
    # fall back to the standard mock_meta so the contract field is always set.
    meta = matches[0].meta if matches else mock_meta(scenario)
    return MatchResponse(matches=matches, meta=meta)


def get_match(user: CurrentUser, role_id: str, scenario: ScenarioId) -> RoleMatch:
    vels, snap_date = _velocities(scenario)
    match = repository.get_match(user.id, role_id, scenario, vels, snap_date)
    if match is None:
        raise NotFoundError(f"No match for role {role_id}")
    return match
