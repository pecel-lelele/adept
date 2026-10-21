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
from app.features.trends import service as trends_service


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

    def fixture_snapshot(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        if snapshot_date is not None and snapshot_date not in trends_mocks.AVAILABLE_MOCK_DATES:
            raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")
        return trends_mocks.snapshot(scenario, snapshot_date)

    monkeypatch.setattr(trends_service, "get_snapshot", fixture_snapshot)
