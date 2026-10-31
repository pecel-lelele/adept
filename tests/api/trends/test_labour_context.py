"""Stored public survey observations retain their own dates and attribution."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.seed import SEED_DIR
from app.features.trends import labour


def test_history_fallback_has_attribution_for_every_month(client: TestClient) -> None:
    response = client.get("/api/v1/trends/malaysia-context/history")
    assert response.status_code == 200
    records = response.json()
    expected = json.loads((SEED_DIR / "trends/malaysia_labour.json").read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["observed_month"] == expected["observed_month"]
    meta = records[0]["meta"]
    assert meta["sources"] == expected["meta"]["sources"]
    assert meta["snapshot_date"] == expected["meta"]["snapshot_date"]
    assert meta["is_estimate"] is False
    assert meta["is_fallback"] is True
    assert meta["served_from"] == "fixture"


def test_stored_history_and_current_use_bounded_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    latest = json.loads((SEED_DIR / "trends/malaysia_labour.json").read_text(encoding="utf-8"))
    # The second observation is a synthetic historical fixture, never a published claim.
    older = deepcopy(latest)
    older["observed_month"] = "2026-07-01"
    older["meta"].update(
        snapshot_date="2026-07-01", observed_from="2026-07-01", observed_to="2026-07-31"
    )
    calls: list[tuple[str, tuple[int]]] = []

    class StoredRows:
        def execute(self, query: str, params: tuple[int]) -> "StoredRows":
            calls.append((query, params))
            return self

        def fetchall(self) -> list[dict[str, Any]]:
            return [{"payload": value} for value in [latest, older][: calls[-1][1][0]]]

    @contextmanager
    def stored_connection() -> Iterator[StoredRows]:
        yield StoredRows()

    monkeypatch.setattr(labour, "use_postgres", lambda: True)
    monkeypatch.setattr(labour, "connection", stored_connection)
    records = labour.history()
    assert [record.observed_month.isoformat() for record in records] == ["2026-08-01", "2026-07-01"]
    assert all(
        record.meta.served_from == "db" and not record.meta.is_fallback for record in records
    )
    assert records[1].meta.snapshot_date.isoformat() == "2026-07-01"
    assert labour.current().observed_month.isoformat() == "2026-08-01"
    assert [params for _, params in calls] == [(120,), (1,)]
    assert all("ORDER BY observed_month DESC LIMIT %s" in query for query, _ in calls)


def test_database_outage_retains_frozen_month(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def unavailable() -> Iterator[None]:
        raise psycopg.OperationalError("synthetic database outage")
        yield

    monkeypatch.setattr(labour, "use_postgres", lambda: True)
    monkeypatch.setattr(labour, "connection", unavailable)
    records = labour.history()
    assert len(records) == 1
    assert records[0].observed_month.isoformat() == "2026-08-01"
    assert records[0].meta.is_fallback is True
