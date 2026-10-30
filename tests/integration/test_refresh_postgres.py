"""Opt-in refresh lease/transaction regressions in an isolated schema of a disposable DB."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.features.data_refresh import automatic_trends, jobs, measurements, repository, service

URL = os.environ.get("ADEPT_REFRESH_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires explicit local refresh-review database")
MIGRATIONS = Path(__file__).resolve().parents[2] / "src/db/migrations"


@pytest.fixture
def pg(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    params = conninfo_to_dict(URL)
    assert params.get("host") in {"127.0.0.1", "localhost"}
    assert params.get("dbname", "").startswith("adept_refresh_review_")
    schema = f"test_refresh_{uuid4().hex}"
    connect = psycopg.connect
    with connect(URL, autocommit=True, row_factory=dict_row) as admin:
        name = admin.execute("SELECT current_database() AS name").fetchone()["name"]
        assert name == params["dbname"]
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        scoped = make_conninfo(
            URL,
            options=f"-c search_path={schema},public -c statement_timeout=5000",
            application_name="adept-refresh-review-fixture",
            connect_timeout=3,
        )
        try:
            with connect(scoped, autocommit=True) as setup:
                for filename in (
                    "20261020160000_m1_trends_signal_tables.sql",
                    "20261022120000_core_trend_snapshot_meta.sql",
                    "20261030160000_data_refresh_runs.sql",
                    "20261030220000_data_refresh_trends.sql",
                    "20261030221000_background_data_refresh.sql",
                    "20261031010000_measured_trend_inputs.sql",
                ):
                    setup.execute((MIGRATIONS / filename).read_text().split("-- migrate:down")[0])

            @contextmanager
            def connection() -> Iterator[Any]:
                with connect(scoped, row_factory=dict_row) as conn:
                    yield conn

            monkeypatch.setattr(repository, "bounded_db_url", lambda: scoped)
            monkeypatch.setattr(measurements, "connection", connection)
            monkeypatch.setattr("app.core.db.connection", connection)
            monkeypatch.setattr(get_settings(), "database_url", scoped)
            yield SimpleNamespace(url=scoped, connect=connect, admin=admin)
        finally:
            # Only this fixture's randomly named schema, in the previously verified DB.
            assert admin.execute("SELECT current_database() AS name").fetchone()["name"] == name
            assert schema.startswith("test_refresh_") and len(schema) == len("test_refresh_") + 32
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def record() -> measurements.MeasuredInputs:
    previous, current = automatic_trends.periods(datetime.now(UTC).date())
    ids = [r["id"] for r in measurements.refdata.rows("taxonomy", "skills")]
    return measurements.MeasuredInputs(
        previous=previous,
        current=current,
        fetched=datetime.now(UTC).date(),
        counts_before={sid: 1 for sid in ids},
        counts_after={sid: 2 for sid in ids},
        total_before=200,
        total_after=200,
        skill_ids=ids,
        labor_decay={},
        automation_exposure={},
        sample=[],
        sources=[
            {
                "name": "Synthetic PostgreSQL regression fixture",
                "url": "https://example.test/measurement",
                "retrieved_at": "2026-10-30",
            }
        ],
        note="Synthetic PostgreSQL regression; no papers or models fetched.",
    )


def test_input_and_snapshot_rollback_before_commit_and_roundtrip_without_inference(pg: Any) -> None:
    inputs = record()
    rows = measurements.rows(inputs)
    stop = threading.Event()
    with pg.connect(pg.url, autocommit=True, row_factory=dict_row) as lease:
        assert lease.execute(
            "SELECT pg_try_advisory_lock(hashtext('adept.data_refresh')) AS held"
        ).fetchone()["held"]
        with repository.use_lease(lease, stop):
            deadline = time.monotonic() + 1
            with pytest.raises((TimeoutError, psycopg.errors.QueryCanceled)):
                with repository.write_connection(deadline) as writer:
                    assert writer is lease
                    measurements.publish(writer, inputs, rows)
                    # Fire after the write phase, before the caller may commit.
                    time.sleep(max(0, deadline - time.monotonic()) + 0.05)
            assert (
                lease.execute("SELECT count(*) AS n FROM measured_trend_inputs").fetchone()["n"]
                == 0
            )
            assert lease.execute("SELECT count(*) AS n FROM trend_snapshots").fetchone()["n"] == 0
            with repository.write_connection(time.monotonic() + 10) as writer:
                measurements.publish(writer, inputs, rows)
        restored = measurements.load(inputs.current[1])
        assert restored == inputs and measurements.rows(restored) == rows
        assert lease.execute("SELECT count(*) AS n FROM trend_snapshots").fetchone()["n"] == len(
            rows
        )


def test_dropped_lease_cancels_and_fences_admin_replacement(
    pg: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = []

    class Idle:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def start(self) -> None:
            launched.append(self)

    monkeypatch.setattr(jobs, "_Thread", Idle)  # no source worker/model is started
    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["trends"])
    monkeypatch.setattr(service, "_storage_ready", lambda: True)
    monkeypatch.setattr(service, "_trends", lambda: SimpleNamespace(data_as_of=None))
    monkeypatch.setattr(jobs, "HEARTBEAT_SECONDS", 0.01)
    first = jobs.start()
    lease, _rid, _due, _steps, stop = launched[0].kwargs["args"]
    finished = threading.Event()
    heartbeat = threading.Thread(
        target=jobs._heartbeat, args=(lease, stop, finished, time.monotonic() + 5)
    )
    heartbeat.start()
    try:
        pid = lease.info.backend_pid
        info = pg.admin.execute(
            "SELECT datname,application_name FROM pg_stat_activity WHERE pid=%s", (pid,)
        ).fetchone()
        assert info["datname"] == conninfo_to_dict(URL)["dbname"]
        assert info["application_name"] == "adept-refresh-review-fixture"
        # Terminate only the session this test just created, never another app connection.
        assert pg.admin.execute("SELECT pg_terminate_backend(%s) AS stopped", (pid,)).fetchone()[
            "stopped"
        ]
        assert stop.wait(3)
        with repository.use_lease(lease, stop), pytest.raises(TimeoutError):
            with repository.write_connection(time.monotonic() + 2):
                pytest.fail("lost lease published")
        second = jobs.start(bypass_cooldown=True)
        assert second.status == "cooldown" and len(launched) == 1
        observed = jobs.status(first.run_id)
        assert observed.status == "failed" and observed.steps[0].error_code == "interrupted"
    finally:
        finished.set()
        heartbeat.join(timeout=3)
        lease.close()
        jobs._active.pop(str(first.run_id), None)
