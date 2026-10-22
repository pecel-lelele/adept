import os
import sys
from pathlib import Path

# Tests use the in-memory stores unless a run opts into PostgreSQL explicitly, so a developer
# .env with M3_BACKEND=postgres never makes the suite read or write their local database.
os.environ["M3_BACKEND"] = os.environ.get("ADEPT_TEST_M3_BACKEND", "csv")
# Never read or write a developer's database: an unreachable address makes every feature use
# its documented fallback (trend snapshots: the frozen export). CI can opt in explicitly.
os.environ["DATABASE_URL"] = os.environ.get(
    "ADEPT_TEST_DATABASE_URL", "postgresql://adept:adept@127.0.0.1:1/adept_test_unreachable"
)
# Test-only auth switches: a raw fixture user id in X-Demo-User, and Aisyah when none is sent.
os.environ["AUTH_RAW_USER_IDS"] = "true"
os.environ["AUTH_DEFAULT_USER"] = "aisyah"
os.environ["SESSION_SECRET"] = "test-only-session-secret"
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/harness

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from harness import fixtures  # noqa: E402

from app.main import app  # noqa: E402

fixtures.install()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_trend_cache() -> None:
    """Each test sees the trend source it sets up, not a snapshot cached by an earlier test."""
    from app.features.trends import service as trends_service

    trends_service.clear_cache()
