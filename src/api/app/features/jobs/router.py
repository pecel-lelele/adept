from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.contracts.common import ScenarioId
from app.contracts.jobs import (
    CertificationList,
    JobBoardPage,
    OpeningsSummary,
    RoleOpenings,
)
from app.core.auth import CurrentUserDep
from app.features.jobs import service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/summary")
def summary(_user: CurrentUserDep, scenario: ScenarioId = "moderate") -> OpeningsSummary:
    """Live openings per Adept role, read from public employer and job-board feeds."""
    return service.summary(scenario)


@router.get("/board")
def board(
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
    role_id: Annotated[str | None, Query(max_length=80)] = None,
    q: Annotated[str, Query(max_length=80)] = "",
    work_mode: Literal["onsite", "hybrid", "remote"] | None = None,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
) -> JobBoardPage:
    """Every live opening matched to an Adept role. With `role_id`, each opening also shows
    which of its skills the learner has now and which their plan adds."""
    return service.board(user, scenario, role_id, q, work_mode, page)


@router.get("/roles/{role_id}")
def role_openings(
    role_id: str,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
    malaysia_focus: bool = False,
) -> RoleOpenings:
    """Current openings for one role, the skills they ask for most, and how many are within the
    learner's reach today and after their plan. With `malaysia_focus`, remote ads open to
    Malaysia or to anyone are included too, each labelled with its Malaysia relevance."""
    return service.role_openings(user, role_id, scenario, limit, malaysia_focus)


@router.get("/certifications")
def certifications(
    user: CurrentUserDep,
    role_id: Annotated[str, Query(max_length=80)],
    scenario: ScenarioId = "moderate",
    payer: Literal["learner", "employer"] = "learner",
) -> CertificationList:
    """Paid certification exams that prove this role's skills, with dated official fees. With
    payer=employer (team programmes) the learner's own skills are not shown."""
    return service.certifications(user, role_id, scenario, payer)
