from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.contracts.common import ScenarioId
from app.contracts.matching import MatchResponse, RoleMatch
from app.core.auth import CurrentUserDep
from app.features.matching import service

router = APIRouter(prefix="/matches", tags=["matching"])

SnapshotDate = Annotated[
    date | None,
    Query(description="Replay an older trend snapshot (YYYY-MM-DD). Omit for the latest."),
]


@router.get("")
def list_matches(
    user: CurrentUserDep, scenario: ScenarioId = "moderate", snapshot_date: SnapshotDate = None
) -> MatchResponse:
    return service.list_matches(user, scenario, snapshot_date)


@router.get("/{role_id}")
def get_match(
    role_id: str,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
    snapshot_date: SnapshotDate = None,
) -> RoleMatch:
    return service.get_match(user, role_id, scenario, snapshot_date)
