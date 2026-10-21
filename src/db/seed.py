"""Load synthetic seed data from src/data/seed/<folder>/<table>.csv.

Usage (from the repo root): .venv/bin/python src/db/seed.py

The CSV file name is the table name and the header row holds column names, so
features add seed data without touching this script. Empty cells become NULL.
Rows that already exist are skipped (ON CONFLICT DO NOTHING), so it is safe to rerun.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg import sql

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
DEFAULT_URL = "postgresql://adept:adept@127.0.0.1:5433/adept"

# Insert order respects foreign keys (see src/db/migrations).
TABLE_ORDER = [
    "users",
    "organizations",
    "memberships",
    "skills",
    "roles",
    "role_skills",
    "profiles",
    "user_skills",
    "snapshots",
    "trend_signals",
    "courses",
    "skill_prerequisites",
    "sdg_goals",
    "sdg_targets",
    "role_sdg_map",
    "skill_sdg_map",
    "org_regions",
]
SERIAL_TABLES = {"snapshots", "trend_signals"}
# CSVs in src/data/seed/ that are evaluation benchmarks or ground truth, not database tables.
NON_TABLE_CSVS = {"expected_roles"}


def collect() -> dict[str, list[Path]]:
    files: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(SEED.glob("*/*.csv")):
        if path.stem in NON_TABLE_CSVS:
            continue
        if path.stem not in TABLE_ORDER:
            raise ValueError(f"{path}: unknown table '{path.stem}' (add it to TABLE_ORDER)")
        files[path.stem].append(path)
    return files


def read_rows(path: Path) -> tuple[list[str], list[list[str | None]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = [[cell if cell != "" else None for cell in row] for row in reader if row]
    return header, rows


def main() -> int:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    files = collect()
    with psycopg.connect(url) as conn:
        for table in TABLE_ORDER:
            for path in files.get(table, []):
                header, rows = read_rows(path)
                query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(map(sql.Identifier, header)),
                    sql.SQL(", ").join(sql.Placeholder() * len(header)),
                )
                with conn.cursor() as cur:
                    cur.executemany(query, rows)
                print(f"{path.relative_to(SEED).as_posix()}: {len(rows)} row(s)")
            if table in SERIAL_TABLES and table in files:
                conn.execute(
                    sql.SQL(
                        "SELECT setval(pg_get_serial_sequence({t}, 'id'), "
                        "COALESCE((SELECT max(id) FROM {i}), 1))"
                    ).format(t=sql.Literal(table), i=sql.Identifier(table))
                )
    print("seed done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
