from fastapi import APIRouter

from app.contracts.impact import ImpactSummary
from app.features.impact import service

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("/summary")
def get_summary() -> ImpactSummary:
    """Public, read-only impact evidence computed on request from the catalogue, the trend
    snapshot and the production matching and pathway engines, on synthetic personas."""
    return service.get_summary()
