from fastapi import APIRouter, Depends

from app.contracts.common import ScenarioId
from app.contracts.guardrails import SyncReport
from app.contracts.pathway import (
    CatalogueResponse,
    Pathway,
    Progress,
    ProgressUpdate,
    ReplanStatus,
    SavedPlan,
    SavePlanIn,
)
from app.core.auth import CurrentUserDep
from app.features.guardrails.datasync import require_sync_token
from app.features.pathway import service, sync

router = APIRouter(prefix="/pathway", tags=["pathway"])


@router.get("")
def get_pathway(role_id: str, user: CurrentUserDep, scenario: ScenarioId = "moderate") -> Pathway:
    return service.get_pathway(user, role_id, scenario)


@router.get("/catalogue")
def get_catalogue() -> CatalogueResponse:
    """Every course the pathway may recommend, with its source and verification date."""
    return service.catalogue()


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
def get_progress(role_id: str, user: CurrentUserDep, scenario: ScenarioId = "moderate") -> Progress:
    return service.get_progress(user, role_id, scenario)


@router.post("/progress")
def update_progress(
    body: ProgressUpdate, user: CurrentUserDep, scenario: ScenarioId = "moderate"
) -> Progress:
    return service.update_progress(user, body, scenario)
