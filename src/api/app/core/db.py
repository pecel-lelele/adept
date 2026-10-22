"""PostgreSQL access. Features call `connection()` from their repository.py.

Connections come from one pool per process. Opening a fresh connection per query cost a TCP and
TLS handshake each time (100-300 ms against a hosted database, several times per request,
starting with the session check). A pooled connection is reused, and every query is bounded by
a server-side statement timeout so one slow query cannot hold a worker forever.

`connection()` keeps psycopg's context-manager semantics: commit on success, roll back on error.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.core.config import get_settings

# Seconds a request waits for a free pooled connection before failing with a database error.
POOL_WAIT_S = 3.0
STATEMENT_TIMEOUT_MS = 10_000
# After a request could not get a connection, others fail fast for this long instead of each
# waiting POOL_WAIT_S, so callers with a fallback (seed files, cached data) answer at once.
DOWN_RETRY_S = 5.0
_down_until: dict[str, float] = {}


def _reset(conn: psycopg.Connection[dict[str, object]]) -> None:
    """Undo per-request client settings before a connection is reused by another request."""
    conn.row_factory = dict_row  # type: ignore[assignment]
    if conn.autocommit:
        conn.autocommit = False


_pools: dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def _pool(url: str) -> ConnectionPool:
    pool = _pools.get(url)
    if pool is not None:
        return pool
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            settings = get_settings()
            pool = ConnectionPool(
                url,
                min_size=0,
                max_size=max(1, settings.db_pool_max),
                timeout=POOL_WAIT_S,
                max_idle=300,
                kwargs={
                    "row_factory": dict_row,
                    "connect_timeout": 3,
                    "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
                },
                open=False,
                reset=_reset,
                name="adept",
            )
            pool.open(wait=False)
            _pools[url] = pool
    return pool


@contextmanager
def connection() -> Iterator[psycopg.Connection[dict[str, object]]]:
    """A pooled connection; the transaction commits when the block exits without an error.

    Raises psycopg.OperationalError at once while the database was unreachable moments ago.
    """
    url = get_settings().database_url
    if time.monotonic() < _down_until.get(url, 0.0):
        raise psycopg.OperationalError("database unavailable (retrying shortly)")
    pool = _pool(url)
    try:
        cm = pool.connection()
        conn = cm.__enter__()
    except PoolTimeout:
        # Every slot in use means busy, not down; with free slots the pool could not connect.
        stats = pool.get_stats()
        if stats.get("pool_size", 0) < stats.get("pool_max", 1):
            _down_until[url] = time.monotonic() + DOWN_RETRY_S
        raise
    _down_until.pop(url, None)
    try:
        yield conn  # type: ignore[misc]
    except BaseException as exc:
        if not cm.__exit__(type(exc), exc, exc.__traceback__):
            raise
    else:
        cm.__exit__(None, None, None)


def close_pools() -> None:
    """Close every pool (application shutdown and tests that swap DATABASE_URL)."""
    with _pools_lock:
        pools = list(_pools.values())
        _pools.clear()
        _down_until.clear()
    for pool in pools:
        pool.close()


def database_status(timeout_s: int = 1) -> str:
    """Return "ok" or "unavailable" (a direct probe, so a full pool cannot hide an outage)."""
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=timeout_s) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except psycopg.Error:
        return "unavailable"
