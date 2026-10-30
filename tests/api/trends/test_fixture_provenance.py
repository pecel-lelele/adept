"""The frozen trend fixtures disclose a historical replay and their real retrieval date."""

from __future__ import annotations

from datetime import date

import pytest

from app.features.trends import mocks
from pipelines.trends import export_fixtures_from_db as exporter


@pytest.mark.parametrize("snapshot_date", mocks.AVAILABLE_MOCK_DATES)
def test_sources_carry_the_recorded_retrieval_date(snapshot_date: date) -> None:
    snap = mocks.snapshot("moderate", snapshot_date)
    retrieved = {s.retrieved_at for s in snap.meta.sources}
    # Retrieval is traceable to the commits that added the raw windows; it is not the replay
    # label, which for 2026-10-13 predates any retrieval in the repository history.
    assert retrieved == {date.fromisoformat(exporter.SOURCES_RETRIEVED_AT)}
    note = snap.meta.data_provenance_note or ""
    assert "Historical replay" in note
    assert snap.meta.observed_to is not None and snap.meta.observed_to.year == 2024


def test_a_re_export_keeps_the_same_disclosure() -> None:
    assert exporter.SOURCES_RETRIEVED_AT == "2026-10-20"
    assert "Historical replay" in exporter.HISTORICAL_REPLAY
