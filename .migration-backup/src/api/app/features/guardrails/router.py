from fastapi import APIRouter, Request

from app.contracts.guardrails import Disclosure, FairnessReport, SourcesResponse
from app.features.guardrails import service

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.get("/disclosure")
def get_disclosure() -> Disclosure:
    """Which language model (if any) is used, for what, and under which rules."""
    return service.get_disclosure()


@router.get("/sources")
def get_sources() -> SourcesResponse:
    """Every data source behind a recommendation, with its date and kind."""
    return service.get_sources()


@router.get("/fairness")
def get_fairness(request: Request) -> FairnessReport:
    """Live fairness checks: protected attributes excluded, counterfactual invariance."""
    return service.get_fairness(request.app)
