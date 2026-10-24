from datetime import date

from fastapi import APIRouter

from app.contracts.scenarios import OutlookResponse, ScenarioListResponse
from app.features.scenarios import service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios() -> ScenarioListResponse:
    return service.list_scenarios()


@router.get("/outlook")
def get_outlook(role_id: str | None = None, snapshot_date: date | None = None) -> OutlookResponse:
    """Role outlooks; ``snapshot_date`` limits the history to that snapshot and earlier."""
    return service.get_outlook(role_id, snapshot_date)
