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
    SharingIn,
    Workspace,
    WorkspaceList,
)
from app.contracts.packages import (
    AcceptPackage,
    AssignedPackage,
    PackageChoice,
    PackageOptions,
    TeamPackage,
)
from app.contracts.programmes import (
    AssignmentDecision,
    MyProgrammes,
    ProgrammeAssignment,
    ProgrammeBriefIn,
    ProgrammeList,
    ProgrammeOptions,
    ProgrammePlan,
    ProgrammeSend,
    ProgrammeStatus,
)
from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import AppError
from app.features.org import funding, packages, programmes, service

router = APIRouter(prefix="/org", tags=["org"])

BudgetYear = Annotated[int, Path(ge=2020, le=2200)]


def _check_workspace(user: CurrentUser, expected_org: str | None) -> None:
    """Reject stale cross-tab submissions where the workspace cookie drifted."""
    if expected_org is not None and expected_org != user.org_id:
        raise AppError(
            "Your workspace changed since this page loaded. Refresh and try again.",
            status_code=409,
            code="workspace_changed",
        )


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
def accept_assigned_package(body: AcceptPackage, user: CurrentUserDep) -> ProgrammeAssignment:
    """Accept HR's team plan as a work programme; the personal plan is left untouched."""
    return packages.accept(user, body.token)


# --- employer programmes: objective-first briefs, personalised routes, agreements ---------


@router.get("/programmes/options")
def programme_options(user: CurrentUserDep) -> ProgrammeOptions:
    """Objectives, roles with team readiness and members, to fill in a programme brief."""
    return programmes.options(user)


@router.post("/programmes/generate")
def generate_programme(
    body: ProgrammeBriefIn,
    user: CurrentUserDep,
    expected_org: Annotated[str | None, Query(max_length=100)] = None,
) -> ProgrammePlan:
    """Propose a personalised route per person for the brief (nothing is saved or sent)."""
    _check_workspace(user, expected_org)
    return programmes.generate(user, body)


@router.post("/programmes", status_code=status.HTTP_201_CREATED)
def send_programme(
    body: ProgrammeSend,
    user: CurrentUserDep,
    expected_org: Annotated[str | None, Query(max_length=100)] = None,
) -> ProgrammeStatus:
    """Send the generated plan to its members (refused if it changed since it was shown)."""
    _check_workspace(user, expected_org)
    return programmes.send(user, body)


@router.get("/programmes")
def list_programmes(user: CurrentUserDep) -> ProgrammeList:
    """Sent programmes with each member's agreement status."""
    return programmes.list_programmes(user)


@router.get("/programmes/mine")
def my_programmes(user: CurrentUserDep) -> MyProgrammes:
    """The signed-in member's work programme assignments and agreements."""
    return programmes.my_programmes(user)


@router.post("/programmes/{programme_id}/decision")
def decide_programme(
    programme_id: Annotated[str, Path(max_length=40)],
    body: AssignmentDecision,
    user: CurrentUserDep,
) -> ProgrammeAssignment:
    """Accept, decline (optional programmes only) or ask HR for a change."""
    return programmes.decide(user, programme_id, body)


@router.get("/funding/{year}")
def get_funding(year: BudgetYear, user: CurrentUserDep) -> FundingLedger:
    return funding.ledger(user, year)


@router.put("/funding/{year}/budget")
def set_member_budget(
    year: BudgetYear, body: MemberBudgetIn, user: CurrentUserDep
) -> FundingLedger:
    return funding.budget(user, year, body)


@router.post("/funding/{year}/requests")
def request_funding(
    year: BudgetYear,
    body: FundingRequest,
    user: CurrentUserDep,
    expected_org: Annotated[str | None, Query(max_length=100)] = None,
) -> FundingLedger:
    _check_workspace(user, expected_org)
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
    """Join as a member with the code a manager or advisor shared. A join code never grants
    management rights; one account can belong to several organisations."""
    return service.join_org(user, data)


@router.get("/workspaces")
def list_workspaces(user: CurrentUserDep) -> WorkspaceList:
    """Workspaces the signed-in person can switch to: personal, then each organisation."""
    return service.workspaces(user)


@router.put("/me/sharing")
def set_sharing(
    data: SharingIn,
    user: CurrentUserDep,
    expected_org: Annotated[str | None, Query(max_length=100)] = None,
) -> Workspace:
    """Member, in the organisation workspace: share (or stop sharing) your skill levels with
    its managers. Personal plans, matches and Adi conversations are never shared."""
    _check_workspace(user, expected_org)
    return service.set_sharing(user, data)


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
