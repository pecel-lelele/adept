from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.contracts.common import ScenarioId
from app.contracts.guardrails import SyncReport
from app.contracts.pathway import (
    CatalogueResponse,
    CourseFormat,
    EvidenceSubmit,
    Pathway,
    Progress,
    ProgressUpdate,
    ProviderType,
    ReplanStatus,
    ReviewDecision,
    SavedPlan,
    SavePlanIn,
    ShareCompletionIn,
    VerificationItem,
    VerificationQueue,
)
from app.core.auth import CurrentUserDep
from app.features.guardrails.datasync import require_sync_token
from app.features.pathway import service, sync

router = APIRouter(prefix="/pathway", tags=["pathway"])


SnapshotDate = Annotated[
    date | None,
    Query(description="Replay an older M1 trend snapshot (YYYY-MM-DD). Omit for the latest."),
]


@router.get("")
def get_pathway(
    user: CurrentUserDep,
    role_id: str | None = None,
    scenario: ScenarioId = "moderate",
    snapshot_date: SnapshotDate = None,
) -> Pathway:
    """The plan for `role_id`; without it, the learner's saved target role."""
    return service.get_pathway(user, service.resolve_role(user, role_id), scenario, snapshot_date)


@router.get("/catalogue")
def get_catalogue(
    skill: Annotated[str | None, Query(max_length=60)] = None,
    format: CourseFormat | None = None,
    audience: Literal["individual", "corporate"] | None = None,
    provider_type: ProviderType | None = None,
    hrd_claimable: bool | None = None,
    max_cost_myr: Annotated[float | None, Query(ge=0)] = None,
) -> CatalogueResponse:
    """Every course the pathway may recommend, with its source and verification date."""
    return service.catalogue(
        service.CatalogueFilter(skill, format, audience, provider_type, hrd_claimable, max_cost_myr)
    )


@router.post("/catalogue/sync", dependencies=[Depends(require_sync_token)])
def sync_catalogue() -> SyncReport:
    """Refresh the catalogue from its live sources (needs X-Sync-Token, M3_BACKEND=postgres)."""
    return sync.sync_catalogue()


@router.post("/plans")
def save_plan(body: SavePlanIn, user: CurrentUserDep) -> SavedPlan:
    """Save the learner's chosen target role and its pathway (the learner decides)."""
    return service.save_plan(user, body)


@router.get("/plans/me")
def get_replan_status(user: CurrentUserDep) -> ReplanStatus:
    """The saved plan, and a proposed re-plan if newer trend data changes it."""
    return service.replan_status(user)


@router.post("/plans/me/accept-replan")
def accept_replan(user: CurrentUserDep) -> SavedPlan:
    return service.accept_replan(user)


@router.get("/progress")
def get_progress(
    user: CurrentUserDep,
    role_id: str | None = None,
    scenario: ScenarioId = "moderate",
) -> Progress:
    """Progress on `role_id` in the current workspace (X-Workspace). Personal: your own plan
    (default: the saved target role). Organisation: your accepted programme for that role
    (default: the newest accepted programme)."""
    return service.get_progress(user, service.progress_role(user, role_id), scenario)


@router.post("/progress")
def update_progress(
    body: ProgressUpdate,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
) -> Progress:
    return service.update_progress(user, body, scenario)


@router.post("/progress/evidence")
def submit_evidence(
    body: EvidenceSubmit,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
) -> Progress:
    """Attach a certificate link to a completed course; it is checked against the provider's
    official verification pages. In an organisation workspace HR reviews it."""
    return service.submit_evidence(user, body, scenario)


@router.post("/progress/share")
def share_completion(
    body: ShareCompletionIn,
    user: CurrentUserDep,
    scenario: ScenarioId = "moderate",
) -> Progress:
    """Organisation workspace: share a course you completed in your personal workspace with
    this programme. HR sees only what you share."""
    return service.share_completion(user, body, scenario)


@router.get("/verifications")
def get_verification_queue(user: CurrentUserDep) -> VerificationQueue:
    """HR / career-centre staff: completions by members of their organisation to review."""
    return service.verification_queue(user)


@router.post("/verifications")
def review_completion(body: ReviewDecision, user: CurrentUserDep) -> VerificationItem:
    """Confirm or reject a member's completion (with an optional note)."""
    return service.review_completion(user, body)
