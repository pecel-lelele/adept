"""Core endpoints (owner M4): health, data freshness and the public platform overview."""

from fastapi import APIRouter

from app.contracts.common import DataFreshness, HealthResponse, PlatformOverview, TrendSource
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
        sources=[TrendSource.model_validate(s.model_dump()) for s in snap.meta.sources],
        is_mock=snap.meta.served_from == "fixture",
        served_from=snap.meta.served_from,
        is_fallback=snap.meta.is_fallback,
        **{
            key: getattr(snap.meta, key)
            for key in (
                "observation_window_start",
                "observation_window_end",
                "retrieved_at",
                "retrieved_at_basis",
                "retrieval_evidence",
                "is_replay",
            )
        },
    )


@router.get("/meta/overview")
def platform_overview() -> PlatformOverview:
    """Live figures for the home page: trends, roles, courses and SDG coverage (no sign-in)."""
    return overview.get()
