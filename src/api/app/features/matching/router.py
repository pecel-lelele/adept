from fastapi import APIRouter

from app.contracts.common import ScenarioId
from app.contracts.matching import MatchResponse, RoleMatch
from app.core.auth import CurrentUserDep
from app.features.matching import service

router = APIRouter(prefix="/matches", tags=["matching"])


@router.get("")
def list_matches(user: CurrentUserDep, scenario: ScenarioId = "moderate") -> MatchResponse:
    return service.list_matches(user, scenario)


@router.get("/{role_id}")
def get_match(role_id: str, user: CurrentUserDep, scenario: ScenarioId = "moderate") -> RoleMatch:
    return service.get_match(user, role_id, scenario)
