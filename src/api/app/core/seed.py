"""Read seed CSVs (src/data/seed/<area>/<table>.csv) for features that run without a DB.

The same files are loaded into PostgreSQL by `make seed`, so mock-mode responses and the
database hold identical data. Rows are cached per file *version* (path, mtime, size), so a
replaced file, e.g. a new trend snapshot, is read again on the next request without a restart
(saved plans live in memory and would be lost by one).
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.core.config import REPO_ROOT

SEED_DIR = REPO_ROOT / "src" / "data" / "seed"

Row = dict[str, str]


@lru_cache(maxsize=128)
def _read(path: Path, mtime_ns: int, size: int) -> tuple[Row, ...]:
    with path.open(encoding="utf-8", newline="") as fh:
        return tuple(dict(row) for row in csv.DictReader(fh))


def rows(area: str, table: str) -> tuple[Row, ...]:
    path = SEED_DIR / area / f"{table}.csv"
    try:
        stat = path.stat()
    except FileNotFoundError:
        return ()
    return _read(path, stat.st_mtime_ns, stat.st_size)


def pg_array(value: str) -> list[str]:
    """Parse a Postgres array literal such as `{a,b}` (the seed format) into a list."""
    inner = value.strip().removeprefix("{").removesuffix("}")
    return [item.strip().strip('"') for item in inner.split(",") if item.strip()]


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "t", "1", "yes"}


def clear_cache() -> None:
    _read.cache_clear()
