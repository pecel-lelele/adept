"""Core endpoints (owner M4): health and data freshness."""

from fastapi import APIRouter

from app.contracts.common import MOCK_SNAPSHOT_DATE, MOCK_SOURCE, DataFreshness, HealthResponse
from app.core.config import get_settings
from app.core.db import database_status

router = APIRouter(tags=["core"])


@router.get("/health")
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.version,
        auth_mode=settings.auth_mode,
        database="ok" if database_status() == "ok" else "unavailable",
    )


@router.get("/meta/data-freshness")
def data_freshness() -> DataFreshness:
    # TODO(F2): read the latest row from `snapshots` once ingestion exists.
    return DataFreshness(snapshot_date=MOCK_SNAPSHOT_DATE, sources=[MOCK_SOURCE], is_mock=True)
