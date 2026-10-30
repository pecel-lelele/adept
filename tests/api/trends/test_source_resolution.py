"""tests/api/trends/test_source_resolution.py

Tests for:
1. Short-TTL retry on failed DB checks (Part 1): temporary DB outage recovers
   without process restart.
2. Authoritative source resolution (Part 2): reachable-but-empty DB resolves
   to fixture (no 404s on advertised dates); populated DB resolves to DB.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.contracts.trends import TrendSnapshotResponse
from app.features.trends import repository


@pytest.mark.parametrize("read_fails", [True, False])
def test_freshness_discloses_database_failure_or_empty_database(
    client: TestClient, read_fails: bool
) -> None:
    repository._reset_db_cache()
    with (
        patch.object(repository, "_get_connection", return_value=MagicMock()),
        patch.object(
            repository,
            "_list_snapshot_dates_db",
            side_effect=RuntimeError("synthetic outage") if read_fails else None,
            return_value=[],
        ),
    ):
        response = client.get("/api/v1/meta/data-freshness")
        assert response.status_code == 200
        assert response.json()["served_from"] == "fixture"
        assert response.json()["is_fallback"] is True
        assert response.json()["is_mock"] is True
        snapshot = client.get("/api/v1/trends/snapshot").json()["meta"]
        assert snapshot["served_from"] == "fixture"
        assert snapshot["is_fallback"] is True


def test_trend_consumers_preserve_fallback_metadata(client: TestClient) -> None:
    from app.features.assistant.context import Context, _trends
    from app.features.pathway import trend_port

    repository._reset_db_cache()
    trend_port.reset_cache()
    try:
        with patch.object(repository, "_get_connection", side_effect=OSError("synthetic outage")):
            for path in (
                "/trends/radar",
                "/matches",
                "/pathway?role_id=data-analyst",
                "/scenarios/outlook",
            ):
                response = client.get(f"/api/v1{path}", headers={"X-Demo-User": "aisyah"})
                assert response.status_code == 200, response.text
                assert response.json()["meta"]["served_from"] == "fixture", path
                assert response.json()["meta"]["is_fallback"] is True, path
            ctx = Context(audience="learner")
            _trends(ctx, "moderate", set())
            assert ctx.meta is not None and ctx.meta.is_fallback
    finally:
        repository._reset_db_cache()
        trend_port.reset_cache()


def test_db_availability_recovers_after_short_ttl(client: TestClient) -> None:
    """A failed DB check is retried after DB_FAILED_RETRY_TTL_S without process restart."""
    repository._reset_db_cache()
    simulated_time = 1000.0

    with (
        patch("time.monotonic", side_effect=lambda: simulated_time),
        patch("app.core.config.get_settings") as mock_settings,
    ):
        mock_settings.return_value.database_url = "postgresql://test:5433/db"

        # 1. DB is initially failing/unavailable
        with patch("app.core.db.database_status", return_value="unavailable"):
            assert repository._db_available() is False
            assert repository.resolve_source() == "fixture"
            resp = client.get("/api/v1/trends/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert "arXiv cs.AI Query API" in [s["name"] for s in data["meta"]["sources"]]

        # 2. Within TTL (e.g. 2s later), check remains cached negative (fast return)
        simulated_time += 2.0
        with patch("app.core.db.database_status", return_value="ok"):
            # Still cached as False because 2s < DB_FAILED_RETRY_TTL_S (5s)
            assert repository._db_available() is False
            assert repository.resolve_source() == "fixture"

        # 3. Beyond TTL (6s later), retry is allowed and detects DB recovery
        simulated_time += 4.0  # total elapsed: 6s > 5s TTL
        with patch("app.core.db.database_status", return_value="ok"):
            # Now retries and discovers DB is ok!
            assert repository._db_available() is True
            # Once positive, it is cached
            assert repository._db_available() is True


def test_reachable_but_empty_database_resolves_to_fixture(client: TestClient) -> None:
    """When PostgreSQL is reachable but trend_snapshots is empty, resolve to fixture.

    GET /api/v1/trends/snapshot with no date must return 200 (NOT 404),
    and meta.available_snapshots must match exactly what can be served.
    """
    repository._reset_db_cache()

    with (
        patch.object(repository, "_db_available", return_value=True),
        patch.object(repository, "_get_connection", return_value=MagicMock()),
        patch.object(repository, "_list_snapshot_dates_db", return_value=[]),
    ):
        # 1. Authoritative source must be "fixture", NOT "db"
        assert repository.resolve_source() == "fixture"

        # 2. Default request with no snapshot_date must return 200
        resp = client.get("/api/v1/trends/snapshot")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = TrendSnapshotResponse.model_validate(resp.json())

        # 3. meta.available_snapshots must match what the fixture serves
        avail = body.meta.available_snapshots
        assert len(avail) >= 2

        # 4. Every advertised date must succeed (no 404s)
        for dt in avail:
            r = client.get(f"/api/v1/trends/snapshot?snapshot_date={dt.isoformat()}")
            assert r.status_code == 200, f"Advertised date {dt} returned {r.status_code}"

        # 5. Non-advertised date must return 404
        r_missing = client.get("/api/v1/trends/snapshot?snapshot_date=1999-01-01")
        assert r_missing.status_code == 404


def test_populated_database_resolves_to_db_and_reflects_db_dates(client: TestClient) -> None:
    """When trend_snapshots has rows, source is 'db' and dates reflect DB availability."""
    repository._reset_db_cache()

    db_dates = [date(2026, 10, 20)]

    with (
        patch.object(repository, "_db_available", return_value=True),
        patch.object(repository, "_get_connection", return_value=MagicMock()),
        patch.object(repository, "_list_snapshot_dates_db", return_value=db_dates),
    ):
        assert repository.resolve_source() == "db"
        assert repository.list_available_dates(source="db") == db_dates

        # Requesting a date only present in fixture (2026-10-13) returns 404 because
        # authoritative source is DB and DB only has 2026-10-20
        resp = client.get("/api/v1/trends/snapshot?snapshot_date=2026-10-13")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


def test_snapshot_request_opens_single_connection_and_single_dates_query(
    client: TestClient,
) -> None:
    """Greptile P2: GET /api/v1/trends/snapshot opens exactly ONE DB connection
    and ONE dates query.
    """
    repository._reset_db_cache()
    # Cache positive DB availability so no extra SELECT 1 connection is made
    repository._db_status_cache = (True, 9999999999.0)

    from unittest.mock import MagicMock, patch

    connect_calls = 0
    executed_queries: list[str] = []

    fake_conn = MagicMock()
    fake_cursor = MagicMock()

    sample_row = {
        "snapshot_date": date(2026, 10, 20),
        "skill_id": "prompt-engineering",
        "research_velocity": 0.45,
        "labor_decay": -0.05,
        "labor_decay_source_note": "BLS 2023-2033",
        "automation_exposure": 0.70,
        "velocity_moderate": 0.25,
        "velocity_fast": 0.55,
        "direction_moderate": "rising",
        "direction_fast": "rising",
    }

    def fake_execute(query: str, params: tuple | None = None) -> None:
        executed_queries.append(query)
        if "SELECT DISTINCT snapshot_date" in query:
            fake_cursor.fetchall.return_value = [{"snapshot_date": date(2026, 10, 20)}]
        elif "SELECT ts.*" in query:
            fake_cursor.fetchall.return_value = [sample_row]

    fake_cursor.execute.side_effect = fake_execute
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    def spy_connect(*args: object, **kwargs: object) -> MagicMock:
        nonlocal connect_calls
        connect_calls += 1
        return fake_conn

    with patch("psycopg.connect", side_effect=spy_connect):
        resp = client.get("/api/v1/trends/snapshot")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["meta"]["scenario"] == "moderate"

        # Assert exactly ONE database connection was opened
        assert connect_calls == 1, f"Expected exactly 1 connection, got {connect_calls}"

        # Assert exactly ONE dates query was issued (not 3)
        dates_queries = [
            q for q in executed_queries if "SELECT DISTINCT snapshot_date FROM trend_snapshots" in q
        ]
        assert len(dates_queries) == 1, (
            f"Expected 1 dates query, got {len(dates_queries)}: {dates_queries}"
        )

        # Assert rows query was executed on the same connection
        rows_queries = [
            q for q in executed_queries if "SELECT ts.*" in q and "FROM trend_snapshots" in q
        ]
        assert len(rows_queries) == 1, f"Expected 1 rows query, got {len(rows_queries)}"
