"""Trends API router (F2 + F3, owner M1).

New endpoint:
  GET /api/v1/trends/snapshot?snapshot_date=<date>&scenario=<moderate|fast>

  GET /api/v1/trends/series?start=&end=&skill_ids=  (observed rolling shares, M1-018)
  GET /api/v1/trends/compare?kind=&entities=&preset=&start=&end=&horizon_days=&mode=  (M1-025)

Legacy endpoints (kept for backward compat):
  GET /api/v1/trends/radar?scenario=<moderate|fast>
  GET /api/v1/trends/roles/{role_id}?scenario=<moderate|fast>
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.common import ScenarioId
from app.contracts.labour import MalaysiaLabourContext
from app.contracts.trends import (
    CompareMode,
    RadarResponse,
    RoleTrendResponse,
    TrendCompareResponse,
    TrendEntityKind,
    TrendRangePreset,
    TrendRefreshStatus,
    TrendRescoreResult,
    TrendSeriesResponse,
    TrendSnapshotResponse,
)
from app.core.auth import CurrentUser, CurrentUserDep
from app.features.trends import comparison, labour, refresh, series, service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/malaysia-context")
def malaysia_context() -> MalaysiaLabourContext:
    return labour.current()


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


@router.get("/series")
def get_series(
    start: date | None = None,
    end: date | None = None,
    skill_ids: Annotated[list[str], Query()] = [],  # noqa: B006 - FastAPI query list default
    scenario: ScenarioId = "moderate",
) -> TrendSeriesResponse:
    """Observed 7-day rolling share per skill for each day in [start, end] (max 366 days).

    Counted from stored papers (no model call). Without `skill_ids`, the three biggest risers
    and fallers in the range are returned. 422 invalid_range for bad dates or skills.
    """
    return series.get_series(start, end, skill_ids, scenario)


@router.get("/compare")
def get_compare(
    kind: TrendEntityKind = "skill",
    entities: Annotated[
        list[str], Query(description="Up to 8 `kind:id` lines. Omit for the biggest movers.")
    ] = [],  # noqa: B006 - FastAPI query list default
    preset: TrendRangePreset | None = None,
    start: date | None = None,
    end: date | None = None,
    scenario: ScenarioId = "moderate",
    horizon_days: Annotated[int, Query(ge=1, le=comparison.MAX_HORIZON)] = (
        comparison.DEFAULT_HORIZON
    ),
    mode: CompareMode = "indexed",
) -> TrendCompareResponse:
    """Skills, roles and categories over a stored range: rebased or raw, with a pace projection.

    Reads stored papers only; never calls arXiv or a model. 422 invalid_range for dates outside
    stored data, unknown entities or more than 8 lines. Role and category scores are derived
    from arXiv skill signals, not observed role demand.
    """
    return comparison.get_compare(kind, entities, preset, start, end, scenario, horizon_days, mode)


# ---------------------------------------------------------------------------
# Legacy endpoints (do not remove – existing tests and frontend depend on them)
# ---------------------------------------------------------------------------


@router.get("/radar")
def get_radar(
    scenario: ScenarioId = "moderate", snapshot_date: date | None = None
) -> RadarResponse:
    return service.get_radar(scenario, snapshot_date)


@router.get("/roles/{role_id}")
def get_role_trend(role_id: str, scenario: ScenarioId = "moderate") -> RoleTrendResponse:
    return service.get_role_trend(role_id, scenario)


# ---------------------------------------------------------------------------
# Admin refresh (signed-in account listed in ADMIN_USER_IDS; checked on the server)
# ---------------------------------------------------------------------------


def _admin(user: CurrentUserDep) -> CurrentUser:
    return refresh.require_admin(user)


@router.post("/refresh", dependencies=[Depends(_admin)])
def start_refresh() -> TrendRefreshStatus:
    """Fetch the latest data: start the trends-refresh GitHub Actions workflow.

    Returns the run already queued or in progress instead of starting a second one.
    503 refresh_not_configured when GITHUB_DISPATCH_TOKEN / GITHUB_REPOSITORY are unset.
    """
    return refresh.dispatch()


@router.get("/refresh/status", dependencies=[Depends(_admin)])
def refresh_status(
    run_id: Annotated[int | None, Query(ge=1, description="GitHub Actions run id.")] = None,
) -> TrendRefreshStatus:
    """Status of a refresh run; a successful run clears the trend caches once."""
    return refresh.status(run_id)


@router.post("/refresh/rescore", dependencies=[Depends(_admin)])
def rescore() -> TrendRescoreResult:
    """Re-score the latest stored signals (no ingest, no model call).

    Publishes only a genuinely new snapshot; otherwise reports no_new_data.
    """
    return refresh.rescore()
