import os
from collections.abc import Iterator

import pytest

from app.core.config import get_settings
from app.features.pathway import repository

PG_URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")


@pytest.fixture(autouse=True)
def _fresh_pathway_state() -> Iterator[None]:
    repository.reset()
    yield
    repository.reset()


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
