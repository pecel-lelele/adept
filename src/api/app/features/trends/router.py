"""Trends API router (F2 + F3, owner M1).

New endpoint:
  GET /api/v1/trends/snapshot?snapshot_date=<date>&scenario=<moderate|fast>

Legacy endpoints (kept for backward compat):
  GET /api/v1/trends/radar?scenario=<moderate|fast>
  GET /api/v1/trends/roles/{role_id}?scenario=<moderate|fast>
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.contracts.common import ScenarioId
from app.contracts.trends import RadarResponse, RoleTrendResponse, TrendSnapshotResponse
from app.features.trends import service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/snapshot")
def get_snapshot(
    snapshot_date: Annotated[
        date | None,
        Query(description="Snapshot date (YYYY-MM-DD). Omit to get the latest available."),
    ] = None,
    scenario: Annotated[
        ScenarioId,
        Query(description="Disruption scenario: 'moderate' or 'fast'."),
    ] = "moderate",
) -> TrendSnapshotResponse:
    """Return the trend snapshot for a given date and scenario.

    The response includes meta.available_snapshots listing every stored date,
    enabling the frontend's trend-replay toggle.
    All scores are pre-computed by the pipeline; no network call is made here.
    """
    return service.get_snapshot(snapshot_date, scenario)


# ---------------------------------------------------------------------------
# Legacy endpoints (do not remove – existing tests and frontend depend on them)
# ---------------------------------------------------------------------------


@router.get("/radar")
def get_radar(scenario: ScenarioId = "moderate") -> RadarResponse:
    return service.get_radar(scenario)


@router.get("/roles/{role_id}")
def get_role_trend(role_id: str, scenario: ScenarioId = "moderate") -> RoleTrendResponse:
    return service.get_role_trend(role_id, scenario)
