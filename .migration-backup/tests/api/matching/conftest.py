"""Matching test fixtures.

Patches M1's trend service with committed fixture snapshots so matching tests
never depend on a live database.  Mirrors the approach in tests/api/pathway/conftest.py.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.contracts.trends import TrendSnapshotResponse
from app.core.errors import NotFoundError
from app.features.trends import mocks as trends_mocks
from app.features.trends import repository as trends_repository
from app.features.trends import service as trends_service


class _FixtureTrendsUnavailableError(Exception):
    """Test double for M1's strict-mode exception before its branch is merged."""


@pytest.fixture(autouse=True)
def _m1_fixture_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve M1's committed fixture snapshots so matching tests never hit the DB.

    The patch is applied to ``trends_service.get_snapshot``, which is the
    function that trend_port._call_with_timeout calls in-process.
    Tests that need a *different* behaviour (e.g. TrendUnavailable, slow call)
    patch ``app.features.matching.service.fetch_snapshot`` directly — that
    patch takes priority over this one at the service level, so these two
    approaches compose cleanly.
    """

    if not hasattr(trends_repository, "TrendsUnavailableError"):
        monkeypatch.setattr(
            trends_repository,
            "TrendsUnavailableError",
            _FixtureTrendsUnavailableError,
            raising=False,
        )

    def fixture_snapshot(
        snapshot_date: date | None, scenario: str, strict: bool = False
    ) -> TrendSnapshotResponse:
        assert strict is False
        if snapshot_date is not None and snapshot_date not in trends_mocks.AVAILABLE_MOCK_DATES:
            raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")
        return trends_mocks.snapshot(scenario, snapshot_date)

    monkeypatch.setattr(trends_service, "get_snapshot", fixture_snapshot)


@pytest.fixture
def strict_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise live matching reads without changing the API's demo identity."""
    from app.features.matching import trend_port

    settings = trend_port.get_settings().model_copy(update={"auth_mode": "supabase"})
    monkeypatch.setattr(trend_port, "get_settings", lambda: settings)
