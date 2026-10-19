"""PostgreSQL access. Features call `connection()` from their repository.py."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings


@contextmanager
def connection() -> Iterator[psycopg.Connection[dict[str, object]]]:
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        yield conn


def database_status(timeout_s: int = 1) -> str:
    """Return "ok" or "unavailable". The skeleton runs on mocks without a database."""
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=timeout_s) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except psycopg.Error:
        return "unavailable"
