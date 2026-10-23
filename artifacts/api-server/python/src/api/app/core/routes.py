"""Core endpoints (owner M4): health, data freshness and the public platform overview."""

from fastapi import APIRouter

from app.contracts.common import DataFreshness, HealthResponse, PlatformOverview, Source
from app.core import overview
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
    """Date and sources of the latest trend snapshot (database, else the frozen export)."""
    from app.features.trends import service as trends_service

    snap = trends_service.get_snapshot(None, "moderate")
    return DataFreshness(
        snapshot_date=snap.meta.snapshot_date,
        sources=[
            Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
        ],
        is_mock=False,
    )


@router.get("/meta/overview")
def platform_overview() -> PlatformOverview:
    """Live figures for the home page: trends, roles, courses and SDG coverage (no sign-in)."""
    return overview.get()
