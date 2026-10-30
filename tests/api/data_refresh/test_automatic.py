"""Shared jobs, scheduler/session separation and no-inference fast paths."""

from __future__ import annotations

import threading
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.features.data_refresh import automatic_trends, jobs, repository, service

NOW = datetime(2026, 10, 30, 8, tzinfo=UTC)
TOKEN = "synthetic-refresh-token-for-tests-only"


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    db = {"held": None, "row": None, "launches": 0}

    class Cursor:
        def __init__(self, row: Any):
            self.row = row

        def fetchone(self) -> Any:
            return self.row

    class Conn:
        def __init__(self) -> None:
            self.identity = object()

        def close(self) -> None:
            if db["held"] is self.identity:
                db["held"] = None

        def execute(self, sql: str, params: Any = ()) -> Cursor:
            if "pg_try_advisory" in sql:
                held = db["held"] is None
                if held:
                    db["held"] = self.identity
                if held and "xact" in sql and db.get("finish_on_probe"):
                    db["row"].update(
                        status="ok",
                        finished_at=NOW,
                        steps=[{"source": "jobs", "status": "done", "rows": 7}],
                    )
                return Cursor({"held": held})
            if sql.startswith("SELECT run_id"):
                row = db["row"]
                if (
                    "status IN ('queued','running')" in sql
                    and row
                    and row["status"] not in ("queued", "running")
                ):
                    row = None
                return Cursor(dict(row) if row else None)
            if sql.startswith("INSERT INTO data_refresh_runs"):
                rid, started, steps = params
                db["row"] = dict(
                    run_id=rid,
                    started_at=started,
                    finished_at=None,
                    status="queued",
                    steps=steps.obj,
                )
            if sql.startswith("UPDATE data_refresh_runs SET status=%s"):
                status, steps, finished, _count, code, _rid = params
                db["row"].update(
                    status=status,
                    steps=steps.obj,
                    finished_at=NOW if finished else None,
                    error_code=code or db["row"].get("error_code"),
                )
            return Cursor(None)

    class Thread:
        def __init__(self, **kw: Any) -> None:
            self.kw = kw

        def start(self) -> None:
            db["launches"] += 1

        def join(self, timeout: float) -> None:
            pass

    monkeypatch.setattr(jobs.psycopg, "connect", lambda *a, **k: Conn())
    monkeypatch.setattr(jobs, "_Thread", Thread)
    monkeypatch.setattr(jobs, "now", lambda: NOW)
    monkeypatch.setattr(service, "_storage_ready", lambda: True)
    monkeypatch.setattr(
        service,
        "_trends",
        lambda: SimpleNamespace(data_as_of=date(2026, 10, 25), is_historical_replay=False),
    )
    monkeypatch.setattr(
        repository, "last_successes", lambda: {s: NOW for s in ("jobs", "courses", "labour")}
    )
    monkeypatch.setattr(get_settings(), "data_refresh_token", TOKEN)
    monkeypatch.setattr(get_settings(), "trends_refresh_cooldown_minutes", 10)
    jobs._active.clear()
    db["Conn"] = Conn
    yield db
    jobs._active.clear()


def test_two_users_attach_to_one_database_locked_run(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["jobs"])
    first = jobs.start()
    second = jobs.start()
    assert first.status == "queued" and second.shared
    assert first.run_id == second.run_id and state["launches"] == 1


def test_fully_current_check_starts_no_job_or_model(state: dict[str, Any]) -> None:
    result = jobs.start()
    assert result.status == "up_to_date" and state["launches"] == 0
    assert result.data_as_of == date(2026, 10, 25)


def test_status_recovers_an_interrupted_worker_without_starting_more_work(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["jobs"])
    result = jobs.start()
    state["held"] = None  # simulate the worker process/session disappearing

    @contextmanager
    def connection() -> Any:
        conn = state["Conn"]()
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr("app.core.db.connection", connection)
    observed = jobs.status(result.run_id)
    assert observed.status == "failed" and observed.finished_at is not None
    failed = next(step for step in observed.steps if step.source == "jobs")
    assert failed.status == "failed" and failed.error_code == "interrupted"
    assert state["launches"] == 1


def test_global_cooldown_and_admin_override(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    state["row"] = dict(
        run_id=uuid4(),
        status="ok",
        started_at=NOW - timedelta(minutes=3),
        finished_at=NOW,
        steps=[],
    )
    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["courses"])
    result = jobs.start()
    assert result.status == "cooldown" and result.retry_at == NOW + timedelta(minutes=7)
    assert state["launches"] == 0
    assert jobs.start(bypass_cooldown=True).status == "queued"
    assert state["launches"] == 1


def test_non_admin_cannot_bypass(
    client: TestClient, state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "admin_user_ids", "")
    assert (
        client.post(
            "/api/v1/data/refresh/check",
            json={"bypass_cooldown": True},
            headers={"X-Demo-User": "aisyah"},
        ).status_code
        == 403
    )
    assert state["launches"] == 0


def test_scheduler_requires_dedicated_token_not_user_session(
    client: TestClient, state: dict[str, Any]
) -> None:
    assert (
        client.post("/api/v1/data/refresh/run", headers={"X-Demo-User": "aisyah"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/data/refresh/run", headers={"X-Data-Refresh-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/data/refresh/run",
            headers={"X-Data-Refresh-Token": TOKEN, "X-Demo-User": "aisyah"},
        ).status_code
        == 403
    )
    response = client.post("/api/v1/data/refresh/run", headers={"X-Data-Refresh-Token": TOKEN})
    assert response.status_code == 200 and response.json()["status"] == "up_to_date"


def test_sources_fail_independently_and_progress_is_persisted(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["jobs", "courses"])
    result = jobs.start()
    thread, _stop = jobs._active[str(result.run_id)]

    def execute(source: str, **kw: Any) -> Any:
        return SimpleNamespace(
            status="failed" if source == "jobs" else "ok",
            rows_upserted=0 if source == "jobs" else 12,
            error_code="fetch_failed" if source == "jobs" else None,
        )

    monkeypatch.setattr(service, "_execute", execute)
    jobs._run(*thread.kw["args"])
    assert state["row"]["status"] == "failed"
    steps = {s["source"]: s for s in state["row"]["steps"]}
    assert steps["jobs"]["status"] == "failed" and steps["courses"]["status"] == "done"
    assert steps["courses"]["rows"] == 12 and state["held"] is None


def test_new_week_skip_precedes_any_runpod_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    _previous, current = automatic_trends.periods(datetime.now(UTC).date())
    note = f"Observed arXiv submissions {current[0]}..{current[1]} against older signals."
    monkeypatch.setattr(
        automatic_trends.refresh, "latest_published", lambda _url: (current[1], note)
    )
    monkeypatch.setattr(
        automatic_trends, "RunPodEncoder", lambda *a, **k: pytest.fail("paid constructor invoked")
    )
    monkeypatch.setattr(automatic_trends, "fetch_window", lambda *a: pytest.fail("network invoked"))
    result = automatic_trends.run(0, 600, threading.Event())
    assert result.rows_upserted == 0 and "no inference" in result.message


def test_paper_publication_dates_must_match_the_actual_window() -> None:
    atom = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
        b"<id>https://arxiv.org/abs/2410.11582</id>"
        b"<published>2024-10-15T00:00:00Z</published>"
        b"<title>Synthetic date regression fixture</title>"
        b"<summary>Synthetic abstract.</summary></entry></feed>"
    )
    with pytest.raises(ValueError, match="outside the measured window"):
        automatic_trends.parse_window(atom, date(2026, 10, 12), date(2026, 10, 18))
    assert automatic_trends.parse_window(atom, date(2024, 10, 14), date(2024, 10, 20))[0][
        "published_at"
    ].startswith("2024")


def test_new_snapshot_uses_measured_week_not_execution_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time
    from contextlib import contextmanager

    latest = []

    class Encoder:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
            return [[1.0] * 384 for _ in texts]

    @contextmanager
    def connection(deadline: float) -> Any:
        yield SimpleNamespace(execute=lambda *args: None)

    monkeypatch.setattr(automatic_trends.refresh, "latest_published", lambda _url: None)
    monkeypatch.setattr(automatic_trends.measurements, "load", lambda *args, **kwargs: None)
    monkeypatch.setattr(automatic_trends, "RunPodEncoder", Encoder)
    monkeypatch.setattr(
        automatic_trends,
        "fetch_window",
        lambda *args: [
            {
                "title": "Synthetic test paper",
                "abstract": "Synthetic sample only.",
                "arxiv_id": "https://arxiv.org/abs/synthetic-fixture",
                "published_at": args[0].isoformat() + "T00:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(repository, "write_connection", connection)
    monkeypatch.setattr(
        automatic_trends.pipeline,
        "publish",
        lambda rows, day, sources, note, _url, **kwargs: latest.append((rows, day, sources, note)),
    )
    monkeypatch.setattr(automatic_trends.refresh, "clear_trend_caches", lambda: None)
    stop = SimpleNamespace(is_set=lambda: False, wait=lambda _seconds: False)
    result = automatic_trends.run(time.monotonic(), 600, stop)
    _previous, current = automatic_trends.periods(datetime.now(UTC).date())
    assert result.rows_upserted > 0 and latest[0][1] == current[1]
    assert latest[0][1] != datetime.now(UTC).date()
    assert latest[0][2][0]["retrieved_at"] == datetime.now(UTC).date().isoformat()
    assert "2024" not in latest[0][3]


def test_database_deadline_cancels_operation_and_prevents_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    cancelled = threading.Event()

    class Conn:
        committed = False
        row_factory = None

        def transaction(self) -> Any:
            return self

        def __enter__(self) -> Any:
            return self

        def __exit__(self, kind: Any, *args: Any) -> None:
            self.committed = kind is None

        def cancel_safe(self, timeout: float) -> None:
            cancelled.set()

    conn = Conn()
    monkeypatch.setattr(repository.psycopg, "connect", lambda *a, **k: conn)
    with pytest.raises(TimeoutError):
        with repository.write_connection(time.monotonic() + 0.02):
            assert cancelled.wait(timeout=1)
    assert cancelled.is_set() and not conn.committed


def test_completion_invalidates_the_polling_instances_caches_once(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(
        automatic_trends.refresh, "clear_trend_caches", lambda: calls.append("trend")
    )
    monkeypatch.setattr(service.refdata, "invalidate", lambda: calls.append("catalogue"))
    row = dict(run_id=uuid4(), status="ok", started_at=NOW, finished_at=NOW, steps=[])
    jobs._response(row)
    jobs._response(row)
    assert calls == ["trend", "catalogue"]


def test_completion_between_status_read_and_lock_probe_is_never_overwritten(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["jobs"])
    result = jobs.start()
    state["held"] = None
    state["finish_on_probe"] = True

    @contextmanager
    def connection() -> Any:
        conn = state["Conn"]()
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr("app.core.db.connection", connection)
    observed = jobs.status(result.run_id)
    assert observed.status == "ok" and observed.steps[0].rows == 7
    assert state["row"]["status"] == "ok" and not state["row"].get("error_code")


def test_lost_session_fences_even_admin_replacement_until_paid_job_policy_expires(
    state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "due_sources", lambda moment: ["trends"])
    jobs.start()
    state["held"] = None
    result = jobs.start(bypass_cooldown=True)
    assert result.status == "cooldown"
    assert result.retry_at == NOW + timedelta(
        seconds=jobs.MAX_JOB_SECONDS + jobs.LEASE_GRACE_SECONDS
    )
    assert state["launches"] == 1 and state["row"]["error_code"] == "interrupted"


def test_heartbeat_loss_signals_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    import psycopg

    class Lost:
        def execute(self, *args: Any) -> None:
            raise psycopg.OperationalError("Synthetic disconnected lease")

    monkeypatch.setattr(jobs, "HEARTBEAT_SECONDS", 0.001)
    stop, finished = threading.Event(), threading.Event()
    jobs._heartbeat(Lost(), stop, finished, time.monotonic() + 1)
    assert stop.is_set()


def test_publication_never_reconnects_a_lost_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    import psycopg

    class Lost:
        def execute(self, *args: Any) -> None:
            raise psycopg.OperationalError("Synthetic disconnected lease")

    monkeypatch.setattr(repository.psycopg, "connect", lambda *a, **k: pytest.fail("reconnected"))
    stop = threading.Event()
    with repository.use_lease(Lost(), stop):
        with pytest.raises(psycopg.OperationalError):
            with repository.write_connection(time.monotonic() + 1):
                pytest.fail("lost lease published")
    assert stop.is_set()


def test_heartbeat_waits_until_a_failed_transaction_has_rolled_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    import psycopg

    checked = threading.Event()
    state = {"in_error": True}

    class Conn:
        def execute(self, *args: Any) -> Any:
            if state["in_error"]:
                raise psycopg.errors.InFailedSqlTransaction("Synthetic rollback in progress")
            checked.set()
            return SimpleNamespace(fetchone=lambda: (1,))

    monkeypatch.setattr(jobs, "HEARTBEAT_SECONDS", 0.001)
    stop, finished, guard = threading.Event(), threading.Event(), threading.RLock()
    with guard:
        heartbeat = threading.Thread(
            target=jobs._heartbeat, args=(Conn(), stop, finished, time.monotonic() + 2, guard)
        )
        heartbeat.start()
        assert not stop.wait(0.02)
        state["in_error"] = False
    try:
        assert checked.wait(1) and not stop.is_set()
    finally:
        finished.set()
        heartbeat.join(timeout=2)
