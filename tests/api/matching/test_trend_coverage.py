"""Prompt 8 (item 12c): the match response must return ``trend_coverage``.

`trend_coverage` is the share of the role's skill importance that had a trend
value in the snapshot; the UI uses it to warn when many skills fell back to
the neutral 0.5.  The field comes from scoring.role_trend via _RoleScore.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.features.matching import service
from app.features.matching.trend_port import TrendSnapshot
from app.features.profile import repository as profile_repo

USER_HEADER = {"X-Demo-User": "weijie"}


@pytest.fixture(autouse=True)
def _isolate_profile_store():
    snapshot = {k: v.model_copy(deep=True) for k, v in profile_repo._store.items()}
    profile_repo._store.clear()
    yield
    profile_repo._store.clear()
    profile_repo._store.update(snapshot)


def _confirm_profile(client: TestClient) -> None:
    resp = client.put(
        "/api/v1/profile/skills/confirm",
        json={"skills": [{"skill_id": "python", "level": 5}, {"skill_id": "sql", "level": 3}]},
        headers=USER_HEADER,
    )
    assert resp.status_code == 200


def test_list_matches_returns_trend_coverage(client: TestClient) -> None:
    """Every real (non-mock) match response contains trend_coverage in [0, 1]."""
    _confirm_profile(client)
    resp = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp.status_code == 200, resp.text

    matches = resp.json()["matches"]
    assert matches, "expected at least one match"
    for m in matches:
        assert "trend_coverage" in m, f"trend_coverage missing for {m['role_id']}"
        assert 0.0 <= m["trend_coverage"] <= 1.0


def test_get_match_returns_trend_coverage(client: TestClient) -> None:
    _confirm_profile(client)
    resp = client.get(
        "/api/v1/matches/data-analyst", params={"scenario": "moderate"}, headers=USER_HEADER
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "trend_coverage" in body
    assert 0.0 <= body["trend_coverage"] <= 1.0


def test_role_with_no_skills_in_snapshot_gives_zero_coverage(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the snapshot covers none of the role's skills, coverage is exactly 0.0."""
    _confirm_profile(client)

    empty_snapshot = TrendSnapshot(
        velocities={"skill-not-in-any-role": 0.9},
        snapshot_date=date(2026, 10, 20),
        sources=[Source(name="Fixture", url="https://example.invalid", retrieved_at="2026-10-20")],
        scenario="moderate",
        is_estimate=True,
    )
    monkeypatch.setattr(service, "fetch_snapshot", lambda scenario: empty_snapshot)

    resp = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp.status_code == 200, resp.text
    for m in resp.json()["matches"]:
        assert m["trend_coverage"] == 0.0, f"{m['role_id']} should have no trend coverage"
