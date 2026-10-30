"""Storage for the live data refresh: run log, cross-instance lock and stored-data freshness.

Every function is bounded by the pool's own timeouts and degrades to "no data" (None / empty)
when the database is unreachable, so the public freshness endpoint never fails because of it.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import tuple_row

from app.contracts.data_refresh import RefreshRunSummary
from app.core.config import get_settings
from app.core.db import connection
from app.core.logging import get_logger
from app.core.refdata import use_postgres

log = get_logger("app.data_refresh.repository")

CONNECT_TIMEOUT_S = 5
STATEMENT_TIMEOUT_MS = 15000


@dataclass(frozen=True)
class Lease:
    conn: Any
    stop: threading.Event
    guard: AbstractContextManager[Any]


_lease: ContextVar[Lease | None] = ContextVar("data_refresh_lease", default=None)


@contextmanager
def use_lease(
    conn: Any, stop: threading.Event, guard: AbstractContextManager[Any] | None = None
) -> Iterator[None]:
    """Publish only on the original session that owns the shared advisory lock."""
    token = _lease.set(Lease(conn, stop, guard if guard is not None else threading.RLock()))
    try:
        yield
    finally:
        _lease.reset(token)


@dataclass(frozen=True)
class StoredFreshness:
    rows: int
    last_fetched_at: date | None
    data_as_of: date | None = None


def bounded_db_url() -> str:
    """DATABASE_URL with connect and statement limits for pipeline writes from the API."""
    return make_conninfo(
        get_settings().database_url,
        connect_timeout=CONNECT_TIMEOUT_S,
        options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c lock_timeout=5000",
    )


@contextmanager
def write_connection(deadline: float) -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    """Cancel active database I/O at the run deadline and roll back instead of committing."""
    if time.monotonic() >= deadline:
        raise TimeoutError("refresh deadline reached")
    lease = _lease.get()
    # Heartbeats cannot run inside a publishing transaction's temporarily failed state.
    with lease.guard if lease else nullcontext():
        with _write_connection(deadline, lease) as conn:
            yield conn


@contextmanager
def _write_connection(deadline: float, lease: Lease | None) -> Iterator[Any]:
    if time.monotonic() >= deadline:
        raise TimeoutError("refresh deadline reached while awaiting the lease guard")
    if lease:
        if lease.stop.is_set():
            raise TimeoutError("refresh lease lost or cancelled")
        try:
            lease.conn.execute("SELECT 1")  # never reconnect a lost lock-owning session
        except psycopg.Error:
            lease.stop.set()
            raise
    managed = nullcontext(lease.conn) if lease else psycopg.connect(bounded_db_url())
    with managed as conn:
        expired = threading.Event()
        previous_factory = conn.row_factory
        conn.row_factory = tuple_row  # pipeline functions use tuple rows, unlike audit queries

        def cancel() -> None:
            expired.set()
            try:
                conn.cancel_safe(timeout=2)
            except psycopg.Error:
                pass  # statement/connect deadlines still bound the operation

        timer = threading.Timer(max(0, deadline - time.monotonic()), cancel)
        timer.daemon = True
        timer.start()
        try:
            # Own the transaction: the check must run BEFORE commit, not after a nested
            # pipeline publisher has already committed an otherwise idle connection.
            with conn.transaction():
                yield conn
                if (
                    expired.is_set()
                    or time.monotonic() >= deadline
                    or (lease and lease.stop.is_set())
                ):
                    raise TimeoutError("refresh deadline or lease lost; transaction rolled back")
        finally:
            timer.cancel()
            timer.join(timeout=2)
            conn.row_factory = previous_factory


_FRESHNESS_SQL = {
    "courses": (
        "SELECT count(*) FILTER (WHERE retired_at IS NULL) AS n, "
        "min(verified_at) FILTER (WHERE retired_at IS NULL) AS fetched, "
        "NULL::date AS as_of FROM courses"
    ),
    "jobs": (
        "SELECT (SELECT count(*) FROM job_postings WHERE active "
        "AND last_seen >= current_date - 14 "
        "AND (expires_at IS NULL OR expires_at >= current_date)) AS n, "
        "coalesce((SELECT max(fetched_on) FROM job_fetch_log WHERE status = 'ok'), "
        "(SELECT max(last_seen) FROM job_postings)) AS fetched, NULL::date AS as_of"
    ),
    "labour": (
        "SELECT count(*) AS n, "
        "max((payload #>> '{meta,sources,0,retrieved_at}')::date) AS fetched, "
        "max(observed_month) AS as_of FROM malaysia_labour_context"
    ),
}


def stored_freshness(source: str) -> StoredFreshness | None:
    """Database facts, or None when serving uses its frozen fallback (or DB is unavailable)."""
    if not use_postgres() or source not in _FRESHNESS_SQL:
        return None
    try:
        with connection() as conn:
            row: Any = conn.execute(_FRESHNESS_SQL[source]).fetchone()  # type: ignore[arg-type]
    except psycopg.Error as exc:
        log.warning("freshness read for %s failed: %s", source, type(exc).__name__)
        return None
    if row is None or (source == "labour" and int(row["n"]) == 0):
        # Labour.current serves the frozen export when this table is empty. Jobs/courses
        # serve a valid empty database result instead, so preserve their zero counts.
        return None
    return StoredFreshness(int(row["n"]), row["fetched"], row["as_of"])


def last_runs() -> dict[str, RefreshRunSummary]:
    if not use_postgres():
        return {}
    try:
        with connection() as conn:
            rows: list[Any] = conn.execute(
                "SELECT DISTINCT ON (source) source, status, finished_at, rows_fetched, "
                "rows_upserted, rows_rejected, error_code FROM data_refresh_runs "
                "WHERE status IN ('ok','failed') AND source <> 'automatic' "
                "ORDER BY source, finished_at DESC"
            ).fetchall()
    except psycopg.Error as exc:
        log.warning("refresh run log read failed: %s", type(exc).__name__)
        return {}
    return {
        str(r["source"]): RefreshRunSummary(
            status=r["status"],
            finished_at=r["finished_at"],
            rows_fetched=r["rows_fetched"],
            rows_upserted=r["rows_upserted"],
            rows_rejected=r["rows_rejected"],
            error_code=r["error_code"],
        )
        for r in rows
    }


def last_successes() -> dict[str, datetime]:
    if not use_postgres():
        return {}
    try:
        with connection() as conn:
            rows = conn.execute(
                "SELECT source,max(finished_at) AS at FROM data_refresh_runs "
                "WHERE status='ok' AND source <> 'automatic' GROUP BY source"
            ).fetchall()
    except psycopg.Error:
        return {}
    return {str(row["source"]): row["at"] for row in rows}


def record_run(
    source: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    rows_fetched: int,
    rows_upserted: int,
    rows_rejected: int,
    error_code: str | None,
    detail: str,
) -> None:
    """Append one run. A logging failure never changes the outcome of the refresh itself."""
    try:
        with connection() as conn:
            conn.execute(
                "INSERT INTO data_refresh_runs (source, started_at, finished_at, status, "
                "rows_fetched, rows_upserted, rows_rejected, error_code, detail) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    source, started_at, finished_at, status, rows_fetched, rows_upserted,
                    rows_rejected, error_code, detail[:300],
                ),
            )  # fmt: skip
    except psycopg.Error as exc:
        log.warning("refresh run log write failed: %s", type(exc).__name__)


@contextmanager
def advisory_lock(source: str) -> Iterator[bool]:
    """Cross-instance lock for one source (Autoscale runs several API instances).

    Yields True when held, False when another instance holds it. Raises psycopg.Error when
    the database cannot be reached. The lock is released when the run ends or the session
    drops, so a crashed instance never blocks the source for long.
    """
    with psycopg.connect(bounded_db_url(), autocommit=True) as conn:
        # Fail before fetching or writing reference data if its audit migration is missing.
        conn.execute("SELECT source, status, finished_at FROM data_refresh_runs LIMIT 0")
        row = conn.execute(
            "SELECT pg_try_advisory_lock(hashtext(%s))", ("adept.data_refresh",)
        ).fetchone()
        held = bool(row and row[0])
        try:
            with use_lease(conn, threading.Event()):
                yield held
        finally:
            if held:
                conn.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("adept.data_refresh",))
