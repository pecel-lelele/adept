from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.contracts.common import ScenarioId
from app.contracts.guardrails import SyncReport
from app.contracts.sdg import (
    EntitySdgLinks,
    RegionListResponse,
    SdgAlignment,
    SdgContribution,
    SdgGoalListResponse,
)
from app.core.auth import CurrentUserDep
from app.features.guardrails.datasync import require_sync_token
from app.features.org import service as org_service
from app.features.sdg import service, sync

router = APIRouter(prefix="/sdg", tags=["sdg"])

GoalId = Annotated[int, Field(ge=1, le=17)]


@router.post("/sync", dependencies=[Depends(require_sync_token)])
def sync_sdg() -> SyncReport:
    """Refresh goals/targets from the UN API and the curated links (needs X-Sync-Token)."""
    return sync.sync_sdg()


@router.get("/goals")
def list_goals() -> SdgGoalListResponse:
    """All 17 goals and 169 targets (UN SDG API), with the domain focus goals flagged."""
    return service.goals()


@router.get("/roles/{role_id}")
def get_role_sdg(role_id: str) -> EntitySdgLinks:
    return service.role_sdg(role_id)


@router.get("/roles/{role_id}/alignment")
def get_role_alignment(
    role_id: str, goals: Annotated[list[GoalId] | None, Query()] = None
) -> SdgAlignment:
    """SDG alignment score for SDG-weighted ranking (F4). Defaults to the focus goals."""
    return service.alignment(role_id, goals or [])


@router.get("/skills/{skill_id}")
def get_skill_sdg(skill_id: str) -> EntitySdgLinks:
    return service.skill_sdg(skill_id)


@router.get("/contribution/me")
def get_my_contribution(
    user: CurrentUserDep, role_id: str | None = None, scenario: ScenarioId = "moderate"
) -> SdgContribution:
    """How the learner's chosen path contributes (role, skills built, plan facts)."""
    return service.my_contribution(user, role_id, scenario)


@router.get("/contribution/org")
def get_org_contribution(
    user: CurrentUserDep, scenario: ScenarioId = "moderate", role_id: str | None = None
) -> SdgContribution:
    """The team's contribution towards ``role_id`` (the role chosen on the team plan), or,
    when omitted, the role where the team's average gap is largest."""
    return service.org_contribution(user.org_id or org_service.DEFAULT_ORG_ID, scenario, role_id)


@router.get("/regions")
def list_regions() -> RegionListResponse:
    return service.regions()


@router.get("/contribution/region/{state}")
def get_region_contribution(
    state: str, scenario: ScenarioId = "moderate", role_id: str | None = None
) -> SdgContribution:
    return service.region_contribution(state, scenario, role_id)
