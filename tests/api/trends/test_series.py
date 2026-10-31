"""Observed rolling skill shares over a chosen date range (paper store, M1-018)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.features.data_refresh import trend_store
from app.features.trends import series

D0 = date(2026, 10, 6)


def test_rolling_share_needs_every_day_of_the_window() -> None:
    days = [D0 + timedelta(days=i) for i in range(9)]
    papers = {d: 10 for d in days if d != D0 + timedelta(days=7)}
    mentions = {(d, "python"): 1 for d in days}
    shares = series.rolling_shares(days[6:], papers, mentions, "python")
    assert shares == [0.1, None, None]  # day 7 is missing: windows ending 7 and 8 are incomplete
    assert series.change([None, 0.1, 0.25, None]) == 0.15
    assert series.change([0.2]) is None


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    days = [D0 + timedelta(days=i) for i in range(21)]
    rising = {(d, "python"): i for i, d in enumerate(days)}
    falling = {(d, "sql"): 20 - i for i, d in enumerate(days)}
    calls: dict[str, Any] = {}

    def daily(start: date, end: date, skill_ids: Any) -> Any:
        calls["skills"] = list(skill_ids)
        papers = {d: 20 for d in days if start <= d <= end}
        both = {**rising, **falling}
        return papers, {k: v for k, v in both.items() if start <= k[0] <= end}

    monkeypatch.setattr(trend_store, "stored_range", lambda: (days[0], days[-1], days[-1]))
    monkeypatch.setattr(trend_store, "daily", daily)
    return calls


def test_default_range_shows_the_biggest_movers_with_attribution(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get("/api/v1/trends/series").json()
    assert body["available_from"] == "2026-10-12" and body["available_to"] == "2026-10-26"
    assert body["start"] == "2026-10-12" and body["end"] == "2026-10-26"
    lines = {line["skill_id"]: line for line in body["lines"]}
    assert lines["python"]["change"] > 0 and lines["sql"]["change"] < 0
    assert len(lines["python"]["points"]) == 15
    meta = body["meta"]
    assert meta["is_estimate"] is False and meta["sources"][0]["url"].startswith("https://")
    assert meta["observed_to"] == "2026-10-26"


def test_chosen_skills_and_range_are_returned_in_order(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(
        "/api/v1/trends/series",
        params={"start": "2026-10-20", "end": "2026-10-26", "skill_ids": ["sql", "python"]},
    ).json()
    assert [line["skill_id"] for line in body["lines"]] == ["sql", "python"]
    assert stored["skills"] == ["sql", "python"]  # only the chosen skills are counted


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-10-26", "end": "2026-10-20"},
        {"start": "2026-01-01", "end": "2026-10-26"},
        {"skill_ids": ["not-a-skill"]},
        {"skill_ids": [f"s{i}" for i in range(9)]},
    ],
)
def test_bad_ranges_and_skills_are_rejected(
    client: TestClient, stored: dict[str, Any], params: dict[str, Any]
) -> None:
    response = client.get("/api/v1/trends/series", params=params)
    assert response.status_code == 422


def test_empty_store_returns_no_lines_instead_of_inventing_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trend_store, "stored_range", lambda: None)
    body = client.get("/api/v1/trends/series").json()
    assert body["lines"] == [] and body["available_to"] is None
