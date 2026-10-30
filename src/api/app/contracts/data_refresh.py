"""Live data refresh and per-source freshness (Core): shared contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DataSourceId = Literal["trends", "courses", "jobs", "labour"]
RefreshableSource = Literal["courses", "catalogue", "jobs", "labour", "trends"]
RefreshRunStatus = Literal["ok", "failed"]


class RefreshRunSummary(BaseModel):
    """The most recent in-app refresh of one source (no secrets, no raw error text)."""

    status: RefreshRunStatus
    finished_at: datetime
    rows_fetched: int = Field(ge=0)
    rows_upserted: int = Field(ge=0)
    rows_rejected: int = Field(ge=0)
    error_code: str | None = None


class DataSourceFreshness(BaseModel):
    """How fresh the data behind one page is, from stored data or run logs (never the clock)."""

    source: DataSourceId
    source_name: str
    source_url: str | None = None
    last_fetched_at: date | None = Field(
        default=None, description="Date the stored data was last fetched/observed from its source."
    )
    data_as_of: date | None = Field(
        default=None,
        description="Period the data describes (snapshot date, observed month), if distinct.",
    )
    snapshot_date: date | None = None
    observed_from: date | None = None
    observed_to: date | None = None
    is_historical_replay: bool = False
    last_success: datetime | None = None
    last_checked_at: datetime | None = None
    age_days: int | None = Field(default=None, ge=0)
    is_stale: bool = False
    rows: int = Field(ge=0)
    served_from: Literal["database", "seed"]
    is_fallback: bool = Field(description="True when the frozen seed export is being served.")
    refreshable: bool = Field(description="An administrator can refresh this source in the app.")
    last_run: RefreshRunSummary | None = None


class DataFreshnessResponse(BaseModel):
    sources: list[DataSourceFreshness]


class DataRefreshResult(BaseModel):
    """Outcome of one admin refresh. A failed run wrote nothing; the last good data stays."""

    source: RefreshableSource
    status: RefreshRunStatus
    started_at: datetime
    finished_at: datetime
    rows_fetched: int = Field(ge=0)
    rows_upserted: int = Field(ge=0)
    rows_rejected: int = Field(ge=0)
    error_code: str | None = None
    message: str
    boards_run: list[str] = Field(default_factory=list)
    boards_skipped: list[str] = Field(default_factory=list)
    freshness: DataSourceFreshness | None = None


class RefreshStep(BaseModel):
    source: DataSourceId
    status: Literal["pending", "running", "done", "failed", "skipped"] = "pending"
    rows: int = 0
    error_code: str | None = None


class BackgroundRefresh(BaseModel):
    run_id: UUID | None = None
    status: Literal["queued", "running", "ok", "failed", "up_to_date", "cooldown"]
    started_at: datetime
    finished_at: datetime | None = None
    checked_at: datetime
    data_as_of: date | None = None
    retry_at: datetime | None = None
    next_scheduled_at: datetime | None = None
    shared: bool = False
    steps: list[RefreshStep] = Field(default_factory=list)


class RefreshCheck(BaseModel):
    bypass_cooldown: bool = False


class RefreshHistory(BaseModel):
    runs: list[BackgroundRefresh]
    next_scheduled_at: datetime
