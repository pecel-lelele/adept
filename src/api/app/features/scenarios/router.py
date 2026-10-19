from fastapi import APIRouter

from app.contracts.scenarios import OutlookResponse, ScenarioListResponse
from app.features.scenarios import service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios() -> ScenarioListResponse:
    return service.list_scenarios()


@router.get("/outlook")
def get_outlook(role_id: str | None = None) -> OutlookResponse:
    return service.get_outlook(role_id)
