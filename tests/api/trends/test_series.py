"""Observed rolling skill shares over a chosen date range (paper store, M1-018)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.features.data_refresh import trend_store
from app.features.trends import series

D0 = date(2026, 10, 6)


def test_daily_counts_share_one_statement_and_preserve_days_without_mentions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    rows = [
        {"day": D0, "papers": 3, "skill_id": "python", "n": 2},
        {"day": D0, "papers": 3, "skill_id": "sql", "n": 1},
        {"day": D0 + timedelta(days=1), "papers": 0, "skill_id": None, "n": None},
    ]

    class Conn:
        def execute(self, query: str, params: Any) -> Any:
            calls.append(query)
            assert len(calls) == 1, "Day totals and mentions must not use separate snapshots"
            assert params == (
                "M1-024",
                D0,
                D0 + timedelta(days=1),
                "M1-024",
                D0,
                D0 + timedelta(days=1),
                ["python", "sql"],
            )
            assert query.count("method = %s") == 2, "one method per series"
            return SimpleNamespace(fetchall=lambda: rows)

    @contextmanager
    def connection() -> Any:
        yield Conn()

    monkeypatch.setattr(trend_store, "connection", connection)
    papers, mentions = trend_store.daily(D0, D0 + timedelta(days=1), ["python", "sql"])
    assert papers == {D0: 3, D0 + timedelta(days=1): 0}
    assert mentions == {(D0, "python"): 2, (D0, "sql"): 1}
    assert len(calls) == 1


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
    # The first plotted point counts papers from six days before it.
    assert meta["observed_from"] == "2026-10-06" and meta["observed_to"] == "2026-10-26"


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
        {"start": "2025-01-01", "end": "2026-10-26"},
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


def test_empty_store_does_not_claim_a_fetch_on_the_requested_end_date(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trend_store, "stored_range", lambda: None)
    response = client.get(
        "/api/v1/trends/series", params={"start": "2027-01-05", "end": "2027-01-10"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["start"] == "2027-01-05" and body["end"] == "2027-01-10"
    assert body["meta"]["observed_from"] is None and body["meta"]["observed_to"] is None
    source = body["meta"]["sources"][0]
    assert "no stored paper observations" in source["name"]
    assert source["url"].endswith("/src/api/app/features/trends/series.py")
    assert source["url"] != series.ARXIV_API
    assert source["retrieved_at"] == body["meta"]["snapshot_date"] == "2026-10-31"


def test_short_history_defaults_to_stored_days_not_an_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    days = [D0 + timedelta(days=i) for i in range(4)]  # fewer than one 7-day window
    monkeypatch.setattr(trend_store, "stored_range", lambda: (days[0], days[-1], days[-1]))
    monkeypatch.setattr(trend_store, "daily", lambda *_a: ({d: 20 for d in days}, {}))
    response = client.get("/api/v1/trends/series")
    assert response.status_code == 200
    body = response.json()
    assert body["start"] == days[0].isoformat() and body["end"] == days[-1].isoformat()
    assert body["lines"] == []
    assert body["available_from"] is None and body["available_to"] == days[-1].isoformat()
    assert body["meta"]["observed_from"] is None and body["meta"]["observed_to"] is None


def test_range_after_stored_history_reports_no_observation_period(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get(
        "/api/v1/trends/series",
        params={"start": "2026-11-05", "end": "2026-11-10", "skill_ids": ["python"]},
    ).json()
    assert all(p["share"] is None for p in body["lines"][0]["points"])
    assert body["meta"]["observed_from"] is None and body["meta"]["observed_to"] is None


def test_range_starting_before_history_reports_plotted_observation_period(
    client: TestClient, stored: dict[str, Any]
) -> None:
    response = client.get(
        "/api/v1/trends/series",
        params={"start": "2026-10-01", "end": "2026-10-14", "skill_ids": ["python"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available_from"] <= body["available_to"]
    assert body["meta"]["observed_from"] == "2026-10-06"
    assert body["meta"]["observed_to"] == "2026-10-14"


def test_short_history_allows_explicit_start_with_default_end(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    days = [D0 + timedelta(days=i) for i in range(4)]
    monkeypatch.setattr(trend_store, "stored_range", lambda: (days[0], days[-1], days[-1]))
    monkeypatch.setattr(trend_store, "daily", lambda *_a: ({d: 20 for d in days}, {}))

    response = client.get("/api/v1/trends/series", params={"start": days[0].isoformat()})

    assert response.status_code == 200
    body = response.json()
    assert body["start"] == days[0].isoformat() and body["end"] == days[-1].isoformat()
