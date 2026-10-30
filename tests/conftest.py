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
# Never call a real language model (or spend a developer's quota) from the test suite.
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_MODEL"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_FALLBACK_MODEL"] = ""
os.environ["LLM_FALLBACK_PROVIDER"] = ""
os.environ["LLM_FALLBACK_API_KEY"] = ""
os.environ["RUNPOD_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["APP_ENV"] = "development"
# Never embed text with a real provider or call the MiniLM RunPod encoder from the suite.
os.environ["EMBEDDINGS_PROVIDER"] = "none"
os.environ["TRENDS_EMBEDDING_BACKEND"] = "runpod"
os.environ["TRENDS_RUNPOD_API_KEY"] = ""
os.environ["TRENDS_RUNPOD_ENDPOINT_ID"] = ""
# Sync endpoints stay off unless a test enables them; proxy trust uses the documented defaults.
os.environ["SYNC_TOKEN"] = ""
os.environ["PROXY_SHARED_SECRET"] = ""
os.environ["TRUSTED_PROXY_HOPS"] = "0"
os.environ["PROXY_CLIENT_IP_MODE"] = "best-effort"
os.environ["WEB_ORIGIN"] = ""
# Keyed job boards are skipped without keys, so the jobs pipeline tests never reach them.
os.environ["CAREERJET_API_KEY"] = ""
os.environ["CAREERJET_LOCALE"] = "en_MY"
os.environ["JOOBLE_API_KEY"] = ""
os.environ["WEB3_CAREER_TOKEN"] = ""
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


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    """Each test gets its own rate-limit allowance (the app keeps one counter per process)."""
    from app.core.security.rate_limit import RateLimitMiddleware

    node = app.middleware_stack
    while node is not None:
        if isinstance(node, RateLimitMiddleware):
            node.counter._windows.clear()
            break
        node = getattr(node, "app", None)


@pytest.fixture(autouse=True)
def _fresh_work_programmes() -> None:
    """Accepted programmes and funding ledgers never leak from one test into the next."""
    from app.features.org import funding_store

    funding_store._memory.clear()
