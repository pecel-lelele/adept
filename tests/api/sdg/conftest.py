from collections.abc import Iterator
from datetime import date

import pytest

from app.contracts.trends import TrendSnapshotResponse
from app.core.errors import NotFoundError
from app.features.pathway import trend_port
from app.features.trends import mocks as trends_mocks
from app.features.trends import service as trends_service


@pytest.fixture(autouse=True)
def _m1_fixture_snapshots(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """SDG contribution builds pathways; serve M1's committed fixtures, never a database."""

    def fixture_snapshot(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        if snapshot_date is not None and snapshot_date not in trends_mocks.AVAILABLE_MOCK_DATES:
            raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")
        return trends_mocks.snapshot(scenario, snapshot_date)

    monkeypatch.setattr(trends_service, "get_snapshot", fixture_snapshot)
    trend_port.reset_cache()
    yield
    trend_port.reset_cache()
