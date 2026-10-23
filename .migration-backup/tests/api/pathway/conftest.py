import os
from collections.abc import Iterator
from datetime import date

import pytest

from app.contracts.trends import TrendSnapshotResponse
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.features.pathway import repository, trend_port
from app.features.trends import mocks as trends_mocks
from app.features.trends import service as trends_service

PG_URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")


@pytest.fixture(autouse=True)
def _m1_fixture_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve M1's committed fixture snapshots, so pathway tests never depend on a database."""

    def fixture_snapshot(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        if snapshot_date is not None and snapshot_date not in trends_mocks.AVAILABLE_MOCK_DATES:
            raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")
        return trends_mocks.snapshot(scenario, snapshot_date)

    monkeypatch.setattr(trends_service, "get_snapshot", fixture_snapshot)


@pytest.fixture(autouse=True)
def _fresh_pathway_state() -> Iterator[None]:
    repository.reset()
    trend_port.reset_cache()
    yield
    repository.reset()
    trend_port.reset_cache()


@pytest.fixture
def pg_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Run against a migrated + seeded PostgreSQL (CI sets ADEPT_TEST_DATABASE_URL)."""
    if not PG_URL:
        pytest.skip("ADEPT_TEST_DATABASE_URL not set")
    settings = get_settings()
    monkeypatch.setattr(settings, "m3_backend", "postgres")
    monkeypatch.setattr(settings, "database_url", PG_URL)
    repository.reset()
    yield
    repository.reset()
