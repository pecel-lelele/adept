"""tests/api/trends/test_source_resolution.py

Tests for:
1. Short-TTL retry on failed DB checks (Part 1): temporary DB outage recovers
   without process restart.
2. Authoritative source resolution (Part 2): reachable-but-empty DB resolves
   to fixture (no 404s on advertised dates); populated DB resolves to DB.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.contracts.trends import TrendSnapshotResponse
from app.features.trends import repository


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
        patch.object(repository, "_list_snapshot_dates_db", return_value=db_dates),
    ):
        assert repository.resolve_source() == "db"
        assert repository.list_available_dates(source="db") == db_dates

        # Requesting a date only present in fixture (2026-10-13) returns 404 because
        # authoritative source is DB and DB only has 2026-10-20
        resp = client.get("/api/v1/trends/snapshot?snapshot_date=2026-10-13")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"
