"""M3 storage switch (F5/F6/F8): seed files + memory, or PostgreSQL.

`M3_BACKEND=postgres` makes pathway state (plans, progress, badges), the course catalogue,
SDG data and rate-limit counters live in `DATABASE_URL`, so they survive restarts and are
shared by every API instance (e.g. on Replit). `csv` (default) keeps the skeleton behaviour.

Reads degrade gracefully: if the database is unreachable they fall back to the seed files
(same rows `make seed` loads) and log a warning. Writes never fall back: they fail with 503 so
nothing is silently lost.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import psycopg
from psycopg import sql

from app.core import seed
from app.core.config import get_settings
from app.core.db import connection
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger("app.refdata")

T = TypeVar("T")

_DB_TABLES_BY_AREA = {
    "courses": frozenset({"courses"}),
    "jobs": frozenset({"certifications", "job_postings"}),
    "pathway": frozenset({"skill_prerequisites"}),
    "sdg": frozenset({"org_regions", "role_sdg_map", "sdg_goals", "sdg_targets", "skill_sdg_map"}),
    "taxonomy": frozenset({"roles", "role_skills", "skills"}),
}
_DB_TABLES = frozenset().union(*_DB_TABLES_BY_AREA.values())


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


def _as_seed_text(value: Any) -> str:
    """Render a DB value the way the seed CSVs store it, so one parser serves both."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "{" + ",".join(str(v) for v in value) + "}"
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _db_rows(
    table: str,
    *,
    active_only: bool = False,
    non_retired_only: bool = False,
    order_by_id: bool = False,
) -> tuple[dict[str, str], ...]:
    if table not in _DB_TABLES or (active_only and non_retired_only):
        raise ValueError("Unsupported reference-data query")
    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
    if active_only:
        query += sql.SQL(" WHERE active")
    elif non_retired_only:
        query += sql.SQL(" WHERE retired_at IS NULL")
    if order_by_id:
        query += sql.SQL(" ORDER BY id")
    with connection() as conn:
        rows = conn.execute(query).fetchall()
    return tuple({k: _as_seed_text(v) for k, v in row.items()} for row in rows)


# Reference rows change only when a sync runs (which calls `invalidate`), so a short cache
# keeps one request from opening a connection per lookup.
CACHE_TTL_S = 30.0
_cache: dict[tuple[str, str, bool, bool, bool], tuple[float, tuple[dict[str, str], ...]]] = {}


def invalidate() -> None:
    _cache.clear()


def rows(
    area: str,
    table: str,
    *,
    active_only: bool = False,
    non_retired_only: bool = False,
    order_by_id: bool = False,
) -> tuple[dict[str, str], ...]:
    """Seed-shaped rows for an M3 reference table: from PostgreSQL when M3_BACKEND=postgres
    (using fixed query options), else from src/data/seed/<area>/<table>.csv."""
    if table not in _DB_TABLES_BY_AREA.get(area, frozenset()):
        raise ValueError("Unsupported reference-data table")
    if not use_postgres():
        return seed.rows(area, table)
    key = (area, table, active_only, non_retired_only, order_by_id)
    hit = _cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1]
    try:
        fresh = _db_rows(
            table,
            active_only=active_only,
            non_retired_only=non_retired_only,
            order_by_id=order_by_id,
        )
    except psycopg.Error as exc:
        log.warning("database read of %s failed, using seed files instead: %s", table, exc)
        return seed.rows(area, table)
    _cache[key] = (now, fresh)
    return fresh
