"""Matching service (F4).

Bridges the HTTP layer -> scoring engine.  Fetches the trend snapshot from
M1's service (via trend_port.fetch_snapshot), builds a RecommendationMeta
directly from the snapshot's own metadata, then delegates to ``repository``.

If the trend snapshot is unavailable, raises TrendUnavailable which the API
maps to 503.  Date and sources always come from the snapshot; never invented.
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.matching import MatchResponse, RoleMatch
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.matching import repository
from app.features.matching.trend_port import fetch_snapshot


def _build_meta(snap, scenario: ScenarioId) -> RecommendationMeta:
    """Map TrendSnapshot fields -> RecommendationMeta field by field."""
    return RecommendationMeta(
        sources=snap.sources,  # list[Source] from snapshot meta
        snapshot_date=snap.snapshot_date,  # date from snapshot meta
        scenario=scenario,
        is_estimate=snap.is_estimate,  # bool from snapshot meta
    )


def list_matches(
    user: CurrentUser, scenario: ScenarioId, snapshot_date: date | None = None
) -> MatchResponse:
    snap = fetch_snapshot(scenario, snapshot_date) if snapshot_date else fetch_snapshot(scenario)
    meta = _build_meta(snap, scenario)
    matches = repository.list_matches(user.id, scenario, snap.velocities, meta)
    if snap.data_provenance_note:
        matches = [
            match.model_copy(update={"data_provenance_note": snap.data_provenance_note})
            for match in matches
        ]
    return MatchResponse(matches=matches, meta=meta, data_provenance_note=snap.data_provenance_note)


def get_match(
    user: CurrentUser, role_id: str, scenario: ScenarioId, snapshot_date: date | None = None
) -> RoleMatch:
    snap = fetch_snapshot(scenario, snapshot_date) if snapshot_date else fetch_snapshot(scenario)
    meta = _build_meta(snap, scenario)
    match = repository.get_match(user.id, role_id, scenario, snap.velocities, meta)
    if match is None:
        raise NotFoundError(f"No match for role {role_id}")
    return match.model_copy(update={"data_provenance_note": snap.data_provenance_note})
