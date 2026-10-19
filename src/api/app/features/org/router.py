from fastapi import APIRouter

from app.contracts.common import ScenarioId
from app.contracts.org import GapHeatmapResponse, GroupPlan, MemberListResponse, Organization
from app.core.auth import CurrentUserDep
from app.features.org import service

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/me")
def get_my_org(user: CurrentUserDep) -> Organization:
    return service.get_my_org(user)


@router.get("/members")
def list_members(user: CurrentUserDep) -> MemberListResponse:
    return service.list_members(user)


@router.get("/gaps")
def get_gaps(user: CurrentUserDep, scenario: ScenarioId = "moderate") -> GapHeatmapResponse:
    return service.get_gaps(user, scenario)


@router.get("/plan")
def get_plan(
    user: CurrentUserDep, scenario: ScenarioId = "moderate", role_id: str | None = None
) -> GroupPlan:
    """Group pathway for a target role; each step lists the members who need it."""
    return service.get_plan(user, scenario, role_id)
