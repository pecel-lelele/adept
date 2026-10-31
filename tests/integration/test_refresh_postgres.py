"""Opt-in refresh lease/transaction regressions in an isolated schema of a disposable DB."""

from __future__ import annotations

import csv
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
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
from app.features.data_refresh import (
    automatic_trends,
    jobs,
    measurements,
    repository,
    service,
    trend_store,
)

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
                    "20261021140000_m1_signal_aggregation_by_fetch_date.sql",
                    "20261022120000_core_trend_snapshot_meta.sql",
                    "20261030160000_data_refresh_runs.sql",
                    "20261030220000_data_refresh_trends.sql",
                    "20261030221000_background_data_refresh.sql",
                    "20261031010000_measured_trend_inputs.sql",
                    "20261031120000_trend_replay_provenance.sql",
                    "20261031180000_trend_paper_store.sql",
                    "20261031220000_trend_matcher_series.sql",
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


def test_series_totals_and_mentions_stay_consistent_during_day_replacement(
    pg: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = date(2026, 10, 6)
    old = [{"arxiv_id": f"synthetic-old-{i}"} for i in range(2)]
    new = [{"arxiv_id": f"synthetic-new-{i}"} for i in range(10)]
    with pg.connect(pg.url) as setup:
        trend_store.save_days(
            setup, {day: old}, {old[0]["arxiv_id"]: ["python"]}, "M1-014", "synthetic-model", day
        )
    changed = False

    class RacingReader:
        def __init__(self, conn: Any) -> None:
            self.conn = conn

        def execute(self, query: str, params: Any) -> Any:
            nonlocal changed
            result = self.conn.execute(query, params)
            if not changed:
                # Commit a real concurrent correction after the first read statement.
                # Separate read statements would pair 2 old papers with 9 new mentions.
                with pg.connect(pg.url) as writer:
                    trend_store.save_days(
                        writer,
                        {day: new},
                        {paper["arxiv_id"]: ["python"] for paper in new[:9]},
                        "M1-014",
                        "synthetic-model",
                        day,
                    )
                changed = True
            return result

    @contextmanager
    def connection() -> Iterator[Any]:
        with pg.connect(pg.url, row_factory=dict_row) as conn:
            yield RacingReader(conn)

    monkeypatch.setenv("TRENDS_MATCHER", "minilm")
    monkeypatch.setattr(trend_store, "connection", connection)
    papers, mentions = trend_store.daily(day, day, ["python"])
    assert changed
    assert papers == {day: 2} and mentions == {(day, "python"): 1}
    with pg.connect(pg.url, row_factory=dict_row) as check:
        assert (
            check.execute("SELECT papers FROM trend_fetched_days WHERE day=%s", (day,)).fetchone()[
                "papers"
            ]
            == 10
        )
    # A later read sees the complete new version, not a mixed 450% result.
    papers, mentions = trend_store.daily(day, day, ["python"])
    assert papers == {day: 10} and mentions == {(day, "python"): 9}
    # Another method's rows for the same day and papers never enter this series (M1-024).
    with pg.connect(pg.url) as writer:
        trend_store.save_days(
            writer,
            {day: new[:1]},
            {new[0]["arxiv_id"]: ["python", "sql"]},
            "M1-024",
            "synthetic-gemini@384",
            day,
        )
    assert trend_store.daily(day, day, ["python", "sql"]) == (
        {day: 10},
        {(day, "python"): 9},
    )
    monkeypatch.setenv("TRENDS_MATCHER", "gemini")
    assert trend_store.daily(day, day, ["python", "sql"]) == (
        {day: 1},
        {(day, "python"): 1, (day, "sql"): 1},
    )


def test_seeding_existing_paper_day_never_mixes_denominators_and_mentions(
    pg: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from db import seed as seed_loader

    existing_day = date(2026, 10, 6)
    new_day = date(2026, 10, 7)
    method = trend_store.MINILM_METHOD
    model = "synthetic-seed-model"
    with pg.connect(pg.url) as conn:
        trend_store.save_days(
            conn,
            {existing_day: [{"arxiv_id": "existing-1"}, {"arxiv_id": "existing-2"}]},
            {"existing-1": ["python"], "existing-2": ["sql"]},
            method,
            model,
            existing_day,
        )

    def csv_file(name: str, header: list[str], rows: list[list[str]]) -> Path:
        path = tmp_path / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    files = {
        "trend_fetched_days": [
            csv_file(
                "trend_fetched_days",
                ["day", "method", "papers", "fetched_on"],
                [
                    [str(existing_day), method, "1", str(existing_day)],
                    [str(new_day), method, "1", str(new_day)],
                ],
            )
        ],
        "trend_paper_mentions": [
            csv_file(
                "trend_paper_mentions",
                ["arxiv_id", "published_on", "method", "model", "skills"],
                [
                    ["old-export-new-id", str(existing_day), method, model, "{python}"],
                    ["new-day-id", str(new_day), method, model, "{python}"],
                ],
            )
        ],
    }
    monkeypatch.setenv("DATABASE_URL", pg.url)
    monkeypatch.setattr(seed_loader, "SEED", tmp_path)
    monkeypatch.setattr(seed_loader, "collect", lambda: files)
    for _ in range(2):
        assert seed_loader.main() == 0

    with pg.connect(pg.url, row_factory=dict_row) as check:
        rows = check.execute(
            "SELECT day, papers FROM trend_fetched_days WHERE method = %s ORDER BY day", (method,)
        ).fetchall()
        assert [(r["day"], r["papers"]) for r in rows] == [(existing_day, 2), (new_day, 1)]
        paper_rows = check.execute(
            "SELECT arxiv_id FROM trend_paper_mentions WHERE method = %s ORDER BY arxiv_id",
            (method,),
        ).fetchall()
        assert [r["arxiv_id"] for r in paper_rows] == ["existing-1", "existing-2", "new-day-id"]

    with pg.connect(pg.url) as conn:
        conn.execute(
            "INSERT INTO trend_matcher_calibration"
            "(model, threshold, rule, reference_rate, reference_papers, calibrated_on) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (model, 0.4, "minilm_mentions_per_paper", 1, 10, existing_day),
        )
    files["trend_matcher_calibration"] = [
        csv_file(
            "trend_matcher_calibration",
            ["model", "threshold", "rule", "reference_rate", "reference_papers", "calibrated_on"],
            [[model, "0.6", "minilm_mentions_per_paper", "1", "10", str(existing_day)]],
        )
    ]
    with pytest.raises(ValueError, match="Seed threshold differs"):
        seed_loader.main()
    with pg.connect(pg.url, row_factory=dict_row) as check:
        assert (
            check.execute(
                "SELECT threshold FROM trend_matcher_calibration WHERE model = %s", (model,)
            ).fetchone()["threshold"]
            == 0.4
        )


def test_export_uses_one_snapshot_during_concurrent_day_replacement(
    pg: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pipelines.trends import backfill

    day = date(2026, 10, 8)
    old = [{"arxiv_id": "synthetic-export-old-1"}, {"arxiv_id": "synthetic-export-old-2"}]
    new = [{"arxiv_id": f"synthetic-export-new-{i}"} for i in range(3)]
    with pg.connect(pg.url) as setup:
        trend_store.save_days(
            setup,
            {day: old},
            {p["arxiv_id"]: ["python"] for p in old},
            trend_store.MINILM_METHOD,
            "synthetic-model",
            day,
        )
    changed = False

    @contextmanager
    def racing_connection() -> Iterator[Any]:
        with pg.connect(pg.url, row_factory=dict_row) as reader:

            class RacingReader:
                def transaction(self) -> Any:
                    return reader.transaction()

                def execute(self, query: str, params: Any = None) -> Any:
                    nonlocal changed
                    result = reader.execute(query, params)
                    if "FROM trend_fetched_days" in query and not changed:
                        with pg.connect(pg.url) as writer:
                            trend_store.save_days(
                                writer,
                                {day: new},
                                {p["arxiv_id"]: ["sql"] for p in new},
                                trend_store.MINILM_METHOD,
                                "synthetic-model",
                                day,
                            )
                        changed = True
                    return result

            yield RacingReader()

    monkeypatch.setenv("TRENDS_MATCHER", "minilm")
    monkeypatch.setattr(backfill, "connection", racing_connection)
    monkeypatch.setattr(backfill, "SEED_DIR", tmp_path / "paper_store")
    assert backfill.export_seed() == 0
    assert changed
    with (backfill.SEED_DIR / "trend_fetched_days.csv").open(newline="") as stream:
        days = list(csv.DictReader(stream))
    with (backfill.SEED_DIR / "trend_paper_mentions.csv").open(newline="") as stream:
        papers = list(csv.DictReader(stream))
    assert len(days) == 1 and days[0]["papers"] == "2"
    assert {p["arxiv_id"] for p in papers} == {p["arxiv_id"] for p in old}
    with pg.connect(pg.url) as check:
        assert (
            check.execute(
                "SELECT papers FROM trend_fetched_days WHERE day = %s AND method = %s",
                (day, trend_store.MINILM_METHOD),
            ).fetchone()[0]
            == 3
        ), "writer really did replace the day between export reads"
