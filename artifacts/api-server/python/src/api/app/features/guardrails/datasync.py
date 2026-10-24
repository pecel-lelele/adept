"""Live data sync plumbing (F8): who may trigger it, and an audit trail of every run.

Sync endpoints are POSTs that call external APIs and rewrite reference tables, so they need
`X-Sync-Token` equal to `SYNC_TOKEN` (compared in constant time) and `M3_BACKEND=postgres`.
Every run, successful or not, is recorded in `data_syncs`; `/guardrails/sources` shows the
last successful sync per source.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

import psycopg
from fastapi import Header
from psycopg.rows import dict_row, tuple_row

from app.contracts.guardrails import SyncReport
from app.core.config import get_settings
from app.core.db import connection
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.refdata import StorageUnavailableError, invalidate, use_postgres

log = get_logger("app.datasync")

# (records, retired, detail)
SyncResult = tuple[int, int, str]


def require_sync_token(x_sync_token: Annotated[str | None, Header()] = None) -> None:
    expected = get_settings().sync_token
    if not expected:
        raise AppError("Sync is disabled (SYNC_TOKEN not set)", status_code=403, code="forbidden")
    if not x_sync_token or not hmac.compare_digest(x_sync_token, expected):
        raise AppError("Invalid sync token", status_code=403, code="forbidden")
    if not use_postgres():
        raise AppError(
            "Live sync writes to PostgreSQL; set M3_BACKEND=postgres",
            status_code=409,
            code="sync_requires_postgres",
        )


def run_logged(
    source: str, job: Callable[[psycopg.Connection[tuple[object, ...]]], SyncResult]
) -> SyncReport:
    """Run `job` in one transaction and record the outcome in `data_syncs`.

    A failed job rolls back completely (the old reference data stays) and is still logged.
    """
    started = datetime.now(UTC)
    try:
        with connection() as conn:
            # Sync jobs read plain tuples; restore dicts before the pooled connection goes back.
            conn.row_factory = tuple_row  # type: ignore[assignment]
            try:
                with conn.transaction():
                    records, retired, detail = job(conn)  # type: ignore[arg-type]
            finally:
                conn.row_factory = dict_row  # type: ignore[assignment]
            status = "ok"
    except psycopg.OperationalError as exc:
        raise StorageUnavailableError(type(exc).__name__) from exc
    except Exception as exc:  # noqa: BLE001 - any source failure is reported, not raised
        log.warning("sync %s failed: %s", source, exc)
        records, retired, detail, status = 0, 0, f"{type(exc).__name__}: {exc}"[:500], "failed"
    finished = datetime.now(UTC)
    with connection() as conn:
        conn.execute(
            "INSERT INTO data_syncs (source, started_at, finished_at, status, records, retired, "
            "detail) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (source, started, finished, status, records, retired, detail),
        )
    invalidate()
    return SyncReport(
        source=source,
        status=status,  # type: ignore[arg-type]
        records=records,
        retired=retired,
        started_at=started,
        finished_at=finished,
        detail=detail,
    )


def last_successful_syncs() -> dict[str, datetime]:
    """source -> finish time of its last successful sync ({} without PostgreSQL)."""
    if not use_postgres():
        return {}
    try:
        with connection() as conn:
            rows = conn.execute(
                "SELECT source, max(finished_at) AS at FROM data_syncs WHERE status = 'ok' "
                "GROUP BY source"
            ).fetchall()
    except psycopg.Error:
        return {}
    return {str(r["source"]): r["at"] for r in rows}  # type: ignore[call-overload]
