from fastapi import APIRouter, status

from app.contracts.common import ScenarioId
from app.contracts.org import (
    GapHeatmapResponse,
    GroupPlan,
    JoinOrgIn,
    MemberListResponse,
    Organization,
    OrganizationIn,
)
from app.core.auth import CurrentUserDep
from app.features.org import service

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/me")
def get_my_org(user: CurrentUserDep) -> Organization:
    return service.get_my_org(user)


@router.put("/me")
def update_my_org(data: OrganizationIn, user: CurrentUserDep) -> Organization:
    """Edit organisation setup (managers and advisors only)."""
    return service.update_my_org(user, data)


@router.post("/me/join-code")
def rotate_join_code(user: CurrentUserDep) -> Organization:
    """Issue a new join code; the old one stops working (managers only)."""
    return service.rotate_join_code(user)


@router.post("/join")
def join_org(data: JoinOrgIn, user: CurrentUserDep) -> Organization:
    """A signed-in learner joins with the code their manager or advisor shared."""
    return service.join_org(user, data)


@router.get("/members")
def list_members(user: CurrentUserDep) -> MemberListResponse:
    return service.list_members(user)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: str, user: CurrentUserDep) -> None:
    service.remove_member(user, member_id)


@router.get("/gaps")
def get_gaps(user: CurrentUserDep, scenario: ScenarioId = "moderate") -> GapHeatmapResponse:
    return service.get_gaps(user, scenario)


@router.get("/plan")
def get_plan(
    user: CurrentUserDep, scenario: ScenarioId = "moderate", role_id: str | None = None
) -> GroupPlan:
    """Group pathway for a target role; each step lists the members who need it."""
    return service.get_plan(user, scenario, role_id)
