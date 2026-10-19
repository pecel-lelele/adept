"""M3 storage switch (F5/F6/F8): seed files + memory, or PostgreSQL.

`M3_BACKEND=postgres` makes pathway state (plans, progress, badges), the course catalogue,
SDG data and rate-limit counters live in `DATABASE_URL`, so they survive restarts and are
shared by every API instance (e.g. on Replit). `csv` (default) keeps the skeleton behaviour.

Reads degrade gracefully: if the database is unreachable they fall back to the seed files
(same rows `make seed` loads) and log a warning. Writes never fall back: they fail with 503 so
nothing is silently lost.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import psycopg

from app.core.config import get_settings
from app.core.db import connection
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger("app.refdata")

T = TypeVar("T")


class StorageUnavailableError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Database unavailable: {detail}", status_code=503, code="storage_unavailable"
        )


def use_postgres() -> bool:
    return get_settings().m3_backend == "postgres"


def fetch_all(sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        rows: list[dict[str, Any]] = conn.execute(sql, params).fetchall()  # type: ignore[arg-type]
        return rows


def read(from_db: Callable[[], T], from_seed: Callable[[], T]) -> T:
    """Reference data: database when M3_BACKEND=postgres, seed files otherwise or on failure."""
    if not use_postgres():
        return from_seed()
    try:
        return from_db()
    except psycopg.Error as exc:
        log.warning("database read failed, using seed files instead: %s", exc)
        return from_seed()
