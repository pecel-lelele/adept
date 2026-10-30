import os
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest

from app.contracts.trends import TrendSnapshotResponse
from app.core import accounts
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.features.org import funding_store
from app.features.org import repository as org_repository
from app.features.pathway import repository, trend_port
from app.features.profile import repository as profile_repository
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
    # These tests persist learning/reference data, while identities and workspaces come
    # from harness.fixtures. Do not look for those memory-only accounts in PostgreSQL
    # or leave negative account-cache entries for subsequent memory-backend tests.
    for module in (accounts, org_repository, profile_repository, funding_store):
        monkeypatch.setattr(module, "use_postgres", lambda: False)
    # Learning workspace foreign keys intentionally require actual organisation rows.
    # Match the synthetic memory identities instead of weakening the storage constraint.
    from harness.workspaces import BANK

    org = org_repository.get_org(BANK)
    assert org is not None
    with psycopg.connect(PG_URL) as conn:
        conn.execute(
            "INSERT INTO organizations(id,type,name) VALUES (%s,%s,%s) ON CONFLICT(id) DO NOTHING",
            (org.id, org.type, org.name),
        )
    accounts._cache.clear()
    repository.reset()
    yield
    accounts._cache.clear()
    repository.reset()
