"""One durable refresh run across API instances; HTTP callers only start/check/poll."""

from __future__ import annotations

import hmac
import threading
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.contracts.data_refresh import (
    BackgroundRefresh,
    DataRefreshResult,
    DataSourceId,
    RefreshStep,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.data_refresh import repository, service

SOURCES = ("trends", "jobs", "courses", "labour")
MAX_JOB_SECONDS = 840
LEASE_GRACE_SECONDS = 15
HEARTBEAT_SECONDS = 1.0
_active: dict[str, tuple[threading.Thread, threading.Event]] = {}
_state_lock = threading.Lock()
_seen_completed: set[str] = set()
_Thread = threading.Thread


def now() -> datetime:
    return datetime.now(UTC)


def require_token(provided: str | None, user_header: str | None = None) -> None:
    expected = get_settings().data_refresh_token
    if not expected:
        raise AppError(
            "Automatic refresh is not configured.", status_code=503, code="refresh_not_configured"
        )
    if user_header or not provided or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise AppError("Invalid scheduler credential.", status_code=403, code="forbidden")


def next_schedule(moment: datetime) -> datetime:
    scheduled = moment.replace(hour=3, minute=41, second=0, microsecond=0)
    return scheduled if scheduled > moment else scheduled + timedelta(days=1)


def _response(row: dict[str, Any], *, shared: bool = False) -> BackgroundRefresh:
    if row["status"] in ("ok", "failed"):
        # A poll may land on another Autoscale instance than the publisher. Clear its
        # read caches too before reporting the completion date or refreshing page data.
        key = str(row["run_id"])
        with _state_lock:
            if key not in _seen_completed:
                from app.core import refdata
                from app.features.trends.refresh import clear_trend_caches

                clear_trend_caches()
                refdata.invalidate()
                if len(_seen_completed) >= 1000:
                    _seen_completed.clear()
                _seen_completed.add(key)
    return BackgroundRefresh(
        run_id=row["run_id"],
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        checked_at=now(),
        shared=shared,
        data_as_of=service._trends().data_as_of,
        next_scheduled_at=next_schedule(now()),
        steps=[RefreshStep.model_validate(step) for step in row["steps"]],
    )


def _latest(conn: Any, *, running: bool = False) -> dict[str, Any] | None:
    condition = "AND status IN ('queued','running')" if running else ""
    return conn.execute(
        "SELECT run_id,status,started_at,finished_at,steps,error_code FROM data_refresh_runs "
        f"WHERE source='automatic' {condition} ORDER BY started_at DESC LIMIT 1"
    ).fetchone()


def due_sources(moment: datetime) -> list[str]:
    """Cheap stored-data cadence check: newest fully announced arXiv day, then daily sources."""
    from app.features.data_refresh.automatic_trends import ARXIV_LAG_DAYS

    current = service._trends()
    newest = moment.date() - timedelta(days=ARXIV_LAG_DAYS)
    due = []
    if current.is_historical_replay or current.data_as_of is None or current.data_as_of < newest:
        due.append("trends")
    successes = repository.last_successes()
    for source in ("jobs", "courses", "labour"):
        if source not in successes or successes[source].date() < moment.date():
            due.append(source)
    return due


def failed_trends_retry_at(conn: Any) -> datetime | None:
    """End of the paid-step backoff if the latest attempted trends step failed."""
    row = conn.execute(
        "SELECT started_at, (SELECT s->>'status' FROM jsonb_array_elements(steps) s "
        "WHERE s->>'source' = 'trends') AS trends FROM data_refresh_runs "
        "WHERE source='automatic' AND EXISTS (SELECT 1 FROM jsonb_array_elements(steps) s "
        "WHERE s->>'source' = 'trends' AND s->>'status' IN ('done','failed')) "
        "ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if not row or row["trends"] != "failed":
        return None
    return row["started_at"] + timedelta(minutes=get_settings().trends_failure_backoff_minutes)


def start(*, bypass_cooldown: bool = False, trends_backoff: bool = False) -> BackgroundRefresh:
    """Start (or attach to) the shared run.

    ``trends_backoff`` (signed-in non-admin checks): after a failed trends step, skip the
    paid MiniLM step until the configured backoff ends; other due sources still run.
    """
    if not service._storage_ready():
        raise AppError(
            "The app database is unavailable.", status_code=503, code="refresh_requires_database"
        )
    moment = now()
    conn = psycopg.connect(repository.bounded_db_url(), autocommit=True, row_factory=dict_row)
    transferred = False
    try:
        held = conn.execute(
            "SELECT pg_try_advisory_lock(hashtext('adept.data_refresh')) AS held"
        ).fetchone()["held"]
        if not held:
            current = _latest(conn, running=True)
            if current:
                return _response(current, shared=True)
            raise AppError(
                "A refresh is starting; retry shortly.", status_code=409, code="refresh_in_progress"
            )
        # Owning the advisory lock proves an old active row lost its DB session, but
        # external work might still be cancelling. Fence replacements until its bounded
        # provider/job lifetime expires; administrator cooldown bypass cannot waive this.
        orphan = _latest(conn, running=True)
        if orphan:
            _interrupt(conn, orphan)
        latest = _latest(conn)
        retry = (
            latest["started_at"] + timedelta(minutes=get_settings().trends_refresh_cooldown_minutes)
            if latest
            else None
        )
        due = due_sources(moment)
        backoff = failed_trends_retry_at(conn) if trends_backoff and "trends" in due else None
        if backoff is not None and moment < backoff:
            due = [source for source in due if source != "trends"]
            if not due:
                return BackgroundRefresh(
                    status="cooldown",
                    started_at=moment,
                    checked_at=moment,
                    retry_at=backoff,
                    data_as_of=service._trends().data_as_of,
                    next_scheduled_at=next_schedule(moment),
                )
        if not due:
            return BackgroundRefresh(
                status="up_to_date",
                started_at=moment,
                checked_at=moment,
                data_as_of=service._trends().data_as_of,
                next_scheduled_at=next_schedule(moment),
            )
        fence = (
            latest["started_at"] + timedelta(seconds=MAX_JOB_SECONDS + LEASE_GRACE_SECONDS)
            if latest and latest.get("error_code") == "interrupted"
            else None
        )
        blocked = fence is not None and moment < fence
        if blocked or (retry and moment < retry and not bypass_cooldown):
            return BackgroundRefresh(
                status="cooldown",
                started_at=moment,
                checked_at=moment,
                retry_at=max(
                    day for day in (fence, None if bypass_cooldown else retry) if day is not None
                ),
                data_as_of=service._trends().data_as_of,
                next_scheduled_at=next_schedule(moment),
            )
        run_id = uuid4()
        steps = [
            RefreshStep(source=source, status="pending" if source in due else "skipped")
            for source in SOURCES
        ]
        from psycopg.types.json import Jsonb

        conn.execute(
            "INSERT INTO data_refresh_runs(run_id,source,status,started_at,finished_at,steps) "
            "VALUES (%s,'automatic','queued',%s,NULL,%s)",
            (run_id, moment, Jsonb([s.model_dump() for s in steps])),
        )
        row = dict(
            run_id=run_id,
            status="queued",
            started_at=moment,
            finished_at=None,
            steps=[s.model_dump() for s in steps],
        )
        stop = threading.Event()
        thread = _Thread(
            target=_run,
            args=(conn, run_id, due, steps, stop),
            name=f"data-refresh-{run_id}",
            daemon=True,
        )
        with _state_lock:
            _active[str(run_id)] = (thread, stop)
        try:
            thread.start()
        except Exception:
            with _state_lock:
                _active.pop(str(run_id), None)
            raise
        transferred = True
        return _response(row)
    finally:
        if not transferred:
            conn.close()  # releases only this session's advisory lock


def _save(
    conn: Any,
    run_id: UUID,
    steps: list[RefreshStep],
    status: str,
    *,
    finished: bool = False,
    error_code: str | None = None,
) -> None:
    from psycopg.types.json import Jsonb

    conn.execute(
        "UPDATE data_refresh_runs SET status=%s,steps=%s,"
        "finished_at=CASE WHEN %s THEN now() ELSE NULL END,rows_upserted=%s,"
        "error_code=coalesce(%s,error_code) WHERE run_id=%s",
        (
            status,
            Jsonb([s.model_dump() for s in steps]),
            finished,
            sum(s.rows for s in steps),
            error_code,
            run_id,
        ),
    )


def _interrupt(conn: Any, row: dict[str, Any]) -> dict[str, Any]:
    steps = [RefreshStep.model_validate(step) for step in row["steps"]]
    for step in steps:
        if step.status in ("running", "pending"):
            step.status = "failed"
            step.error_code = "interrupted"
    _save(conn, row["run_id"], steps, "failed", finished=True, error_code="interrupted")
    return {
        **row,
        "status": "failed",
        "finished_at": now(),
        "error_code": "interrupted",
        "steps": [step.model_dump() for step in steps],
    }


def _heartbeat(
    conn: Any,
    stop: threading.Event,
    finished: threading.Event,
    deadline: float,
    guard: AbstractContextManager[Any] | None = None,
) -> None:
    import time

    while not finished.wait(HEARTBEAT_SECONDS):
        try:
            if time.monotonic() >= deadline:
                stop.set()
                return
            with guard if guard is not None else nullcontext():
                if finished.is_set():
                    return
                conn.execute("SELECT 1").fetchone()
        except Exception:
            stop.set()  # MiniLM observes this and cancels; publication uses this lost session.
            return


def _run(
    conn: Any, run_id: UUID, due: list[str], steps: list[RefreshStep], stop: threading.Event
) -> None:
    import time

    deadline = time.monotonic() + MAX_JOB_SECONDS
    finished = threading.Event()
    guard = threading.RLock()
    heartbeat = threading.Thread(
        target=_heartbeat,
        args=(conn, stop, finished, deadline, guard),
        daemon=True,
        name=f"refresh-lease-{run_id}",
    )
    try:
        heartbeat.start()
        _save(conn, run_id, steps, "running")
        for step in steps:
            if step.source not in due:
                continue
            if stop.is_set() or time.monotonic() >= deadline:
                step.status = "failed"
                step.error_code = "time_budget_reached"
                continue
            step.status = "running"
            _save(conn, run_id, steps, "running")
            try:
                with repository.use_lease(conn, stop, guard):
                    result = _source_step(step.source, deadline, stop)
                step.status = "done" if result.status == "ok" else "failed"
                step.rows = result.rows_upserted
                step.error_code = result.error_code
            except Exception as exc:
                # Provider text/URLs can contain credentials. Persist only a controlled code.
                step.status = "failed"
                step.error_code = type(exc).__name__
            _save(conn, run_id, steps, "running")
        _save(
            conn,
            run_id,
            steps,
            "failed" if any(s.status == "failed" for s in steps) else "ok",
            finished=True,
        )
    except Exception:
        # A lost DB session releases the lock; the next run marks this one interrupted.
        pass
    finally:
        finished.set()
        if heartbeat.ident is not None:
            heartbeat.join(timeout=3)
        stop.set()
        conn.close()
        with _state_lock:
            _active.pop(str(run_id), None)


def _source_step(source: DataSourceId, deadline: float, stop: threading.Event) -> DataRefreshResult:
    import time

    from app.features.data_refresh import automatic_trends

    if source == "trends":

        def runner(started: float, budget: float) -> service.Outcome:
            return automatic_trends.run(started, min(budget, deadline - time.monotonic()), stop)

        return service._execute(
            "trends", runner=runner, limit=min(600, deadline - time.monotonic())
        )
    return service._execute(source, limit=min(90, deadline - time.monotonic()))


def status(run_id: UUID) -> BackgroundRefresh:
    from app.core.db import connection

    with connection() as conn:
        row = conn.execute(
            "SELECT run_id,status,started_at,finished_at,steps,error_code FROM data_refresh_runs "
            "WHERE run_id=%s AND source='automatic'",
            (run_id,),
        ).fetchone()
        if row and row["status"] in ("queued", "running"):
            # A transaction-scoped probe cannot release the worker's session lock.
            # Acquiring it proves that worker no longer exists, even on another instance.
            held = conn.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext('adept.data_refresh')) AS held"
            ).fetchone()["held"]
            if held:
                # The worker may have finished between our initial read and lock probe.
                row = conn.execute(
                    "SELECT run_id,status,started_at,finished_at,steps,error_code "
                    "FROM data_refresh_runs WHERE run_id=%s AND source='automatic' FOR UPDATE",
                    (run_id,),
                ).fetchone()
                if row and row["status"] in ("queued", "running"):
                    row = _interrupt(conn, row)
    if not row:
        raise AppError("Refresh run not found.", status_code=404, code="not_found")
    return _response(row)


def recent() -> list[BackgroundRefresh]:
    from app.core.db import connection

    with connection() as conn:
        rows = conn.execute(
            "SELECT run_id,status,started_at,finished_at,steps FROM data_refresh_runs "
            "WHERE source='automatic' ORDER BY started_at DESC LIMIT 5"
        ).fetchall()
    return [_response(row) for row in rows]


def shutdown() -> None:
    with _state_lock:
        active = list(_active.values())
    for _thread, stop in active:
        stop.set()  # RunPod's poll/submit boundary observes this and cancels its active job.
    for thread, _stop in active:
        thread.join(timeout=3)
