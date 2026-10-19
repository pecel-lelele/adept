from fastapi import APIRouter

from app.contracts.sdg import EntitySdgLinks, SdgContribution
from app.core.auth import CurrentUserDep
from app.features.sdg import service

router = APIRouter(prefix="/sdg", tags=["sdg"])


@router.get("/roles/{role_id}")
def get_role_sdg(role_id: str) -> EntitySdgLinks:
    return service.role_sdg(role_id)


@router.get("/skills/{skill_id}")
def get_skill_sdg(skill_id: str) -> EntitySdgLinks:
    return service.skill_sdg(skill_id)


@router.get("/contribution/me")
def get_my_contribution(user: CurrentUserDep) -> SdgContribution:
    return service.my_contribution(user)
