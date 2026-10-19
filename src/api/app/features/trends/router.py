from fastapi import APIRouter

from app.contracts.common import ScenarioId
from app.contracts.trends import RadarResponse, RoleTrendResponse
from app.features.trends import service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/radar")
def get_radar(scenario: ScenarioId = "moderate") -> RadarResponse:
    return service.get_radar(scenario)


@router.get("/roles/{role_id}")
def get_role_trend(role_id: str, scenario: ScenarioId = "moderate") -> RoleTrendResponse:
    return service.get_role_trend(role_id, scenario)
