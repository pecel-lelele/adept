"""The frozen trend fixtures disclose a historical replay and their real retrieval date."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.features.trends import mocks
from pipelines.trends import export_fixtures_from_db as exporter


@pytest.mark.parametrize("snapshot_date", mocks.AVAILABLE_MOCK_DATES)
def test_sources_carry_the_recorded_retrieval_date(snapshot_date: date) -> None:
    snap = mocks.snapshot("moderate", snapshot_date)
    retrieved = {s.retrieved_at for s in snap.meta.sources}
    # The fixture commit day is disclosed as a fallback, never as a verified fetch time.
    assert retrieved == {snap.meta.retrieved_at} == {date(2026, 10, 24)}
    assert snap.meta.retrieved_at_basis == "git_commit_date"
    assert snap.meta.is_replay is True
    for source in snap.meta.sources:
        assert source.retrieved_at_basis == "git_commit_date"
        assert source.retrieval_evidence == snap.meta.retrieval_evidence
        assert "fetch time unverified" in (source.retrieval_evidence or "")
    assert snap.meta.observed_to is not None and snap.meta.observed_to.year == 2024


def test_a_re_export_keeps_the_same_disclosure() -> None:
    import json

    frozen = json.loads(
        (exporter.SEED_DIR / "mock_trends_2026-10-20.json").read_text(encoding="utf-8")
    )
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = frozen["items"]
    cursor.fetchone.return_value = {
        **frozen["meta"],
        "provenance_note": frozen["meta"]["data_provenance_note"],
    }
    exported = exporter.export_snapshot(conn, "2026-10-20", {})
    for field in (
        "is_replay",
        "observation_window_start",
        "observation_window_end",
        "retrieved_at",
        "retrieved_at_basis",
        "retrieval_evidence",
        "sources",
    ):
        assert exported["meta"][field] == frozen["meta"][field]
