"""Live data refresh + freshness API (Core).

GET  /api/v1/data/freshness              public, read-only: per-source freshness
POST /api/v1/data/refresh/{source}       admin only: courses | jobs | labour, in process
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from app.contracts.data_refresh import (
    BackgroundRefresh,
    DataFreshnessResponse,
    DataRefreshResult,
    RefreshableSource,
    RefreshCheck,
    RefreshHistory,
)
from app.core.admin import require_admin
from app.core.auth import CurrentUser, CurrentUserDep, get_current_user
from app.features.data_refresh import jobs, service

router = APIRouter(prefix="/data", tags=["data"])


def _admin(user: CurrentUserDep) -> CurrentUser:
    return require_admin(user)


@router.get("/freshness")
def data_freshness() -> DataFreshnessResponse:
    """When each data source was last fetched (from stored data or run logs) and where it is
    served from. Page requests never fetch upstream data."""
    return service.freshness()


def _scheduler(
    x_data_refresh_token: Annotated[str | None, Header()] = None,
    x_demo_user: Annotated[str | None, Header()] = None,
) -> None:
    jobs.require_token(x_data_refresh_token, x_demo_user)


def _status_access(
    x_data_refresh_token: Annotated[str | None, Header()] = None,
    x_demo_user: Annotated[str | None, Header()] = None,
) -> None:
    if x_data_refresh_token:
        jobs.require_token(x_data_refresh_token, x_demo_user)
    else:
        get_current_user(x_demo_user)


@router.post("/refresh/run", dependencies=[Depends(_scheduler)], status_code=202)
def scheduled_run(response: Response) -> BackgroundRefresh:
    result = jobs.start()
    if result.status in ("up_to_date", "cooldown"):
        response.status_code = 200
    return result


@router.post("/refresh/check", status_code=202)
def user_refresh(data: RefreshCheck, user: CurrentUserDep, response: Response) -> BackgroundRefresh:
    if data.bypass_cooldown:
        require_admin(user)
    result = jobs.start(bypass_cooldown=data.bypass_cooldown)
    if result.status in ("up_to_date", "cooldown"):
        response.status_code = 200
    return result


@router.get("/refresh/status/{run_id}", dependencies=[Depends(_status_access)])
def run_status(run_id: UUID) -> BackgroundRefresh:
    return jobs.status(run_id)


@router.get("/refresh/recent", dependencies=[Depends(_admin)])
def recent_runs() -> RefreshHistory:
    return RefreshHistory(runs=jobs.recent(), next_scheduled_at=jobs.next_schedule(jobs.now()))


@router.post("/refresh/{source}", dependencies=[Depends(_admin)])
def refresh_source(source: RefreshableSource) -> DataRefreshResult:
    """Fetch, validate and upsert one source into the app database (admin only).

    409 refresh_in_progress while that source is running; 501 refresh_not_supported when the
    pipeline is not installed here; 503 when the database is not available. A failed run
    (status "failed") wrote nothing and the last good data stays served.
    """
    return service.refresh(source)
