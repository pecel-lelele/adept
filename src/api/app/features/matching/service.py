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
from app.contracts.matching import (
    MatchResponse,
    ReplayDriver,
    ReplayResponse,
    RoleMatch,
    RoleMovement,
)
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.matching import replay_diff, repository, sdg_weight
from app.features.matching.scoring import Weights
from app.features.matching.trend_port import fetch_snapshot


def _build_meta(snap, scenario: ScenarioId) -> RecommendationMeta:
    """Map TrendSnapshot fields -> RecommendationMeta field by field."""
    return RecommendationMeta(
        sources=snap.sources,  # list[Source] from snapshot meta
        snapshot_date=snap.snapshot_date,  # date from snapshot meta
        scenario=scenario,
        is_estimate=snap.is_estimate,  # bool from snapshot meta
        observed_from=snap.observed_from,
        observed_to=snap.observed_to,
        served_from=snap.served_from,
        is_fallback=snap.is_fallback,
    )


def _weighted(matches: list[RoleMatch], weight: float) -> list[RoleMatch]:
    if weight <= 0:
        return matches
    links = {m.role_id: sdg_weight.default_links(m.role_id) for m in matches}
    impact = sdg_weight.sdg_impact(links, lambda rid: links[rid])
    notes = {rid: sdg_weight.review_note(found) for rid, found in links.items()}
    return sdg_weight.apply(matches, impact, weight, notes)


def list_matches(
    user: CurrentUser,
    scenario: ScenarioId,
    snapshot_date: date | None = None,
    sdg_weight_value: float = 0.0,
) -> MatchResponse:
    snap = fetch_snapshot(scenario, snapshot_date) if snapshot_date else fetch_snapshot(scenario)
    meta = _build_meta(snap, scenario)
    matches = repository.list_matches(
        user.id, scenario, snap.velocities, meta, snap.reference_velocities
    )
    if snap.data_provenance_note:
        matches = [
            match.model_copy(update={"data_provenance_note": snap.data_provenance_note})
            for match in matches
        ]
    matches = _weighted(matches, sdg_weight_value)
    return MatchResponse(matches=matches, meta=meta, data_provenance_note=snap.data_provenance_note)


def get_match(
    user: CurrentUser,
    role_id: str,
    scenario: ScenarioId,
    snapshot_date: date | None = None,
    sdg_weight_value: float = 0.0,
) -> RoleMatch:
    snap = fetch_snapshot(scenario, snapshot_date) if snapshot_date else fetch_snapshot(scenario)
    meta = _build_meta(snap, scenario)
    if sdg_weight_value > 0:
        # Impact is relative to the strongest role, so score the full list and pick one.
        everyone = repository.list_matches(
            user.id, scenario, snap.velocities, meta, snap.reference_velocities
        )
        match = next(
            (m for m in _weighted(everyone, sdg_weight_value) if m.role_id == role_id), None
        )
    else:
        match = repository.get_match(
            user.id, role_id, scenario, snap.velocities, meta, snap.reference_velocities
        )
    if match is None:
        raise NotFoundError(f"No match for role {role_id}")
    return match.model_copy(update={"data_provenance_note": snap.data_provenance_note})


def replay(
    user: CurrentUser,
    scenario: ScenarioId,
    from_date: date,
    to_date: date | None = None,
    sdg_weight_value: float = 0.0,
) -> ReplayResponse:
    """Rank the learner on two snapshot dates and explain each role's movement.

    With a UN Goals weight the same SDG blend as the matches list applies to both dates.
    """
    before = fetch_snapshot(scenario, from_date)
    after = fetch_snapshot(scenario, to_date) if to_date else fetch_snapshot(scenario)
    if before.snapshot_date == after.snapshot_date:
        raise AppError(
            "Pick an earlier snapshot to compare with.", status_code=422, code="same_snapshot"
        )
    profile = repository.load_profile(user.id)
    roles = repository.load_roles()
    impact = (
        sdg_weight.sdg_impact([r.role_id for r in roles], sdg_weight.default_links)
        if sdg_weight_value > 0
        else None
    )
    rows = replay_diff.compare(
        profile,
        roles,
        before.velocities,
        after.velocities,
        Weights(),
        impact=impact,
        sdg_weight=sdg_weight_value,
        reference_before=before.reference_velocities,
        reference_after=after.reference_velocities,
    )
    movements = [
        RoleMovement(
            role_id=m.role_id,
            label=repository.role_label(m.role_id),
            rank_before=m.rank_before,
            rank_after=m.rank_after,
            score_before=m.score_before,
            score_after=m.score_after,
            drivers=[
                ReplayDriver(
                    skill_id=d.skill_id,
                    label=repository.skill_label(d.skill_id),
                    velocity_before=d.velocity_before,
                    velocity_after=d.velocity_after,
                    position_before=d.position_before,
                    position_after=d.position_after,
                    effect=d.effect,
                )
                for d in found
            ],
        )
        for m, found in rows
    ]
    return ReplayResponse(
        scenario=scenario,
        from_date=before.snapshot_date.isoformat(),
        to_date=after.snapshot_date.isoformat(),
        movements=movements,
        meta=_build_meta(after, scenario),
    )
