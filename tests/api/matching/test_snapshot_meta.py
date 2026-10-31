"""Tests for item 3 of PR-#4 review: snapshot date and sources.

Rules:
- meta.snapshot_date must equal the trend snapshot''s date, never today().
- meta.sources must equal the snapshot''s sources, never the mock source.
- When the trend provider is unavailable, the API returns 503.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.features.matching.trend_port import TrendSnapshot, TrendUnavailable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SNAP_DATE = date(2026, 10, 20)
# "today" is deliberately one day later to prove snapshot_date != today()
_TODAY = date(2026, 10, 21)

_SNAP_SOURCE = Source(
    name="O*NET 28.2",
    url="https://www.onetcenter.org/",
    retrieved_at=_SNAP_DATE,
)

_GOOD_SNAPSHOT = TrendSnapshot(
    velocities={"python": 0.8, "sql": 0.5},
    snapshot_date=_SNAP_DATE,
    sources=[_SNAP_SOURCE],
    scenario="moderate",
    is_estimate=True,
)

# Patch target: service.py imports fetch_snapshot by name, so patch it there.
_FETCH_PATCH = "app.features.matching.service.fetch_snapshot"


def _fake_fetch_good(scenario: str) -> TrendSnapshot:  # noqa: ARG001
    return _GOOD_SNAPSHOT


def _fake_fetch_unavailable(scenario: str) -> TrendSnapshot:  # noqa: ARG001
    raise TrendUnavailable("Trend service is down (test)")


def test_available_snapshots_come_from_the_ranking_read(client: TestClient) -> None:
    dates = [date(2026, 10, 13), _SNAP_DATE]
    snapshot = replace(_GOOD_SNAPSHOT, available_snapshots=dates)
    with patch(_FETCH_PATCH, return_value=snapshot) as fetch:
        response = client.get("/api/v1/matches", params={"scenario": "moderate"})
    assert response.status_code == 200
    assert response.json()["meta"]["available_snapshots"] == [d.isoformat() for d in dates]
    fetch.assert_called_once_with("moderate")


def test_trend_adapter_preserves_available_snapshots() -> None:
    from app.features.matching.trend_port import fetch_snapshot
    from app.features.trends import mocks

    snapshot = mocks.snapshot("moderate")
    with patch("app.features.matching.trend_port._call_with_timeout", return_value=snapshot):
        result = fetch_snapshot("moderate")
    assert result.available_snapshots == snapshot.meta.available_snapshots
    assert result.available_snapshots is not snapshot.meta.available_snapshots


# ---------------------------------------------------------------------------
# Test 1: snapshot date propagates correctly, never today()
# ---------------------------------------------------------------------------


def test_meta_snapshot_date_comes_from_snapshot_not_today(client: TestClient) -> None:
    """Snapshot is 2026-10-20; real today is 2026-10-21.

    The response meta.snapshot_date must be 2026-10-20 (from the snapshot),
    not today''s date.  We verify by asserting the exact value and that it
    differs from today.
    """
    with patch(_FETCH_PATCH, side_effect=_fake_fetch_good):
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert resp.status_code == 200
    body = resp.json()
    snap_date_str = body["meta"]["snapshot_date"]
    assert snap_date_str == "2026-10-20", (
        f"Expected 2026-10-20 (snapshot date), got {snap_date_str!r}"
    )
    assert snap_date_str != str(_TODAY), "snapshot_date must not be today()"


# ---------------------------------------------------------------------------
# Test 2: sources come from snapshot, not mock source
# ---------------------------------------------------------------------------


def test_meta_sources_come_from_snapshot(client: TestClient) -> None:
    """Sources in meta must equal the snapshot''s sources, not the mock source."""
    with patch(_FETCH_PATCH, side_effect=_fake_fetch_good):
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert resp.status_code == 200
    sources = resp.json()["meta"]["sources"]
    assert len(sources) == 1, f"Expected 1 source, got {len(sources)}: {sources}"
    assert sources[0]["name"] == "O*NET 28.2", (
        f"Expected real source name, got {sources[0]['name']!r}"
    )
    assert sources[0]["name"] != "MOCK DATA", "Sources must not be the mock source"


# ---------------------------------------------------------------------------
# Test 3: per-match meta also carries real snapshot date and sources
# ---------------------------------------------------------------------------


def test_per_match_meta_carries_real_snapshot(client: TestClient) -> None:
    """Every RoleMatch.meta must also carry the real snapshot date and sources."""
    with patch(_FETCH_PATCH, side_effect=_fake_fetch_good):
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert resp.status_code == 200
    matches = resp.json()["matches"]
    assert matches, "Expected at least one match"
    for m in matches:
        assert m["meta"]["snapshot_date"] == "2026-10-20", (
            f"Match {m['role_id']}: snapshot_date mismatch"
        )
        assert m["meta"]["sources"][0]["name"] == "O*NET 28.2", (
            f"Match {m['role_id']}: source name mismatch"
        )


# ---------------------------------------------------------------------------
# Test 4: unavailable trend provider -> 503
# ---------------------------------------------------------------------------


def test_trend_unavailable_returns_503(client: TestClient) -> None:
    """When the trend provider raises TrendUnavailable, the API must return 503."""
    with patch(_FETCH_PATCH, side_effect=_fake_fetch_unavailable):
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert resp.status_code == 503, f"Expected 503 Service Unavailable, got {resp.status_code}"
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "trend_unavailable"
