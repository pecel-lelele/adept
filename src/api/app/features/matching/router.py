from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.contracts.common import ScenarioId
from app.contracts.matching import MatchResponse, ReplayResponse, RoleMatch
from app.core.auth import CurrentUserDep
from app.features.matching import service

router = APIRouter(prefix="/matches", tags=["matching"])

SnapshotDate = Annotated[
    date | None,
    Query(description="Replay an older trend snapshot (YYYY-MM-DD). Omit for the latest."),
]


SdgWeight = Annotated[
    float,
    Query(
        ge=0,
        le=1,
        description=(
            "How much the UN Goals count in the ranking, 0..1. 0 (default) keeps the standard "
            "score; above 0 adds an 'sdg_impact' part and scales the others down."
        ),
    ),
]
ToDate = Annotated[date | None, Query(description="The later snapshot; latest if omitted.")]
FromDate = Annotated[date, Query(description="The earlier snapshot (YYYY-MM-DD).")]


@router.get("")
def list_matches(
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
    snapshot_date: SnapshotDate = None,
    sdg_weight: SdgWeight = 0.0,
) -> MatchResponse:
    return service.list_matches(user, scenario, snapshot_date, sdg_weight)


@router.get("/replay")
def replay(
    user: CurrentUserDep,
    from_date: FromDate,
    scenario: ScenarioId = "moderate",
    to_date: ToDate = None,
    sdg_weight: SdgWeight = 0.0,
) -> ReplayResponse:
    """What changed in the learner's role ranking between two snapshots, and why."""
    return service.replay(user, scenario, from_date, to_date, sdg_weight)


@router.get("/{role_id}")
def get_match(
    role_id: str,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
    snapshot_date: SnapshotDate = None,
    sdg_weight: SdgWeight = 0.0,
) -> RoleMatch:
    return service.get_match(user, role_id, scenario, snapshot_date, sdg_weight)
