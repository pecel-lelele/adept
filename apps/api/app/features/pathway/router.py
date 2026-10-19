from fastapi import APIRouter

from app.contracts.common import ScenarioId
from app.contracts.pathway import Pathway
from app.core.auth import CurrentUserDep
from app.features.pathway import service

router = APIRouter(prefix="/pathway", tags=["pathway"])


@router.get("")
def get_pathway(role_id: str, user: CurrentUserDep, scenario: ScenarioId = "moderate") -> Pathway:
    return service.get_pathway(user, role_id, scenario)
