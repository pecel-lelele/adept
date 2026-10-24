"""H09: snapshots say which period their evidence measures, not only their demo date."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.features.trends.provenance import observation_window, window_from_note

AISYAH = {"X-Demo-User": "aisyah"}


def test_window_is_read_from_the_note_or_explicit_fields() -> None:
    note = "measured from arXiv windows 2024-10-13..2024-10-19 vs 2024-10-06..2024-10-12"
    assert window_from_note(note) == (date(2024, 10, 13), date(2024, 10, 19))
    assert window_from_note("no dates here") == (None, None)
    assert window_from_note(None) == (None, None)
    explicit = {"observed_from": "2026-10-12", "observed_to": "2026-10-18"}
    assert observation_window(explicit, note) == (date(2026, 10, 12), date(2026, 10, 18))


def test_snapshot_and_match_meta_carry_the_observed_period(client: TestClient) -> None:
    snap = client.get("/api/v1/trends/snapshot").json()["meta"]
    if snap.get("observed_to"):
        assert snap["observed_to"] <= snap["snapshot_date"]
        matches = client.get("/api/v1/matches", headers=AISYAH).json()["meta"]
        assert matches["observed_to"] == snap["observed_to"]
