from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.contracts.common import ScenarioId
from app.contracts.funding import (
    FundingCompletion,
    FundingDecision,
    FundingLedger,
    FundingRequest,
    FundingSubmission,
    MemberBudgetIn,
)
from app.contracts.org import (
    GapHeatmapResponse,
    GroupPlan,
    JoinOrgIn,
    MemberListResponse,
    Organization,
    OrganizationIn,
)
from app.contracts.packages import (
    AcceptPackage,
    AssignedPackage,
    PackageChoice,
    PackageOptions,
    TeamPackage,
)
from app.contracts.pathway import SavedPlan
from app.core.auth import CurrentUserDep
from app.features.org import funding, packages, service

router = APIRouter(prefix="/org", tags=["org"])

BudgetYear = Annotated[int, Path(ge=2020, le=2200)]


@router.get("/packages")
def get_packages(
    user: CurrentUserDep,
    role_id: str | None = None,
    member_ids: Annotated[list[str] | None, Query(max_length=50)] = None,
    scenario: ScenarioId = "moderate",
) -> PackageOptions:
    return packages.options(user, role_id, member_ids, scenario)


@router.post("/packages/select")
def select_package(body: PackageChoice, user: CurrentUserDep) -> TeamPackage:
    return packages.select(user, body)


@router.get("/packages/assigned")
def get_assigned_package(user: CurrentUserDep) -> AssignedPackage | None:
    return packages.assigned(user)


@router.post("/packages/assigned/accept")
def accept_assigned_package(body: AcceptPackage, user: CurrentUserDep) -> SavedPlan:
    return packages.accept(user, body.token)


@router.get("/funding/{year}")
def get_funding(year: BudgetYear, user: CurrentUserDep) -> FundingLedger:
    return funding.ledger(user, year)


@router.put("/funding/{year}/budget")
def set_member_budget(
    year: BudgetYear, body: MemberBudgetIn, user: CurrentUserDep
) -> FundingLedger:
    return funding.budget(user, year, body)


@router.post("/funding/{year}/requests")
def request_funding(year: BudgetYear, body: FundingRequest, user: CurrentUserDep) -> FundingLedger:
    return funding.request(user, year, body)


@router.post("/funding/{year}/requests/{claim_id}/submit")
def submit_funding_claim(
    year: BudgetYear,
    claim_id: str,
    body: FundingSubmission,
    user: CurrentUserDep,
) -> FundingLedger:
    return funding.submit(user, year, claim_id, body)


@router.post("/funding/{year}/requests/{claim_id}/completion")
def complete_funded_course(
    year: BudgetYear,
    claim_id: str,
    body: FundingCompletion,
    user: CurrentUserDep,
) -> FundingLedger:
    return funding.complete(user, year, claim_id, body)


@router.post("/funding/{year}/requests/{claim_id}/decision")
def decide_funding(
    year: BudgetYear,
    claim_id: str,
    body: FundingDecision,
    user: CurrentUserDep,
) -> FundingLedger:
    return funding.decide(user, year, claim_id, body)


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
