import pytest

from app.core.security.rate_limit import RateLimitMiddleware
from app.features.profile import repository as profile_repo
from app.main import app


@pytest.fixture(autouse=True)
def reset_profile_rate_limits() -> None:
    """Clear sliding window rate limits before each profile test to prevent 429 flake."""
    curr = getattr(app, "middleware_stack", None)
    while curr:
        if isinstance(curr, RateLimitMiddleware):
            curr.counter._windows.clear()
        curr = getattr(curr, "app", None)
    yield


@pytest.fixture(autouse=True)
def isolate_profile_store() -> None:
    """Restore the in-memory profile store after each profile test.

    These tests save demo-user profiles (hours_per_week, budget, interests).  Without
    a restore, a later feature that reads the same demo users (F5 pathway, F4 matching)
    sees the leftover values whenever pytest runs profile before them.
    """
    saved = {k: v.model_copy(deep=True) for k, v in profile_repo._store.items()}
    yield
    profile_repo._store.clear()
    profile_repo._store.update(saved)
