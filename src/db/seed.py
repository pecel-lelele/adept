"""Load synthetic seed data from src/data/seed/<folder>/<table>.csv.

Usage (from the repo root): .venv/bin/python src/db/seed.py

The CSV file name is the table name and the header row holds column names, so
features add seed data without touching this script. Empty cells become NULL.
Reference records are upserted by key so enrichment reaches existing deployments.
Accounts, profiles and immutable dated trend exports are never overwritten.
"""

from __future__ import annotations

import csv
import json
import os
import struct
import sys
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.features.trends.provenance import (  # noqa: E402
    PROVENANCE_FIELDS,
    lock_snapshot,
    provenance_values,
)

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
    "certifications",
    "job_postings",
    "org_regions",
    # Portable trend paper store (src/data/seed/trends/paper_store, M1-027). Existing rows are
    # kept, so re-seeding never replaces a day the live job has since refetched.
    "trend_fetched_days",
    "trend_paper_mentions",
    "trend_matcher_calibration",
]
REFERENCE_KEYS = {
    "skills": ("id",),
    "roles": ("id",),
    "role_skills": ("role_id", "skill_id"),
    "courses": ("id",),
    "skill_prerequisites": ("skill_id", "prerequisite_id"),
    "sdg_goals": ("id",),
    "sdg_targets": ("id",),
    "role_sdg_map": ("role_id", "sdg_target_id"),
    "skill_sdg_map": ("skill_id", "sdg_target_id"),
    "certifications": ("id",),
    "job_postings": ("id",),
}

SERIAL_TABLES = {"snapshots", "trend_signals"}
# CSVs in src/data/seed/ that are evaluation benchmarks or ground truth, not database tables.
NON_TABLE_CSVS = {"expected_roles", "role_categories"}
# Synthetic people and organisations are test / evaluation fixtures only. The database holds
# reference data (taxonomy, courses, SDGs, trends); every user and organisation in it is
# created through the app's own sign-up flow.
FIXTURE_ONLY_DIRS = {"personas", "org"}
FIXTURE_ONLY_TABLES = {"org_regions"}  # regions of the fixture organisations


def collect() -> dict[str, list[Path]]:
    files: dict[str, list[Path]] = defaultdict(list)
    for path in sorted([*SEED.glob("*/*.csv"), *SEED.glob("trends/paper_store/*.csv")]):
        if (
            path.stem in NON_TABLE_CSVS | FIXTURE_ONLY_TABLES
            or path.parent.name in FIXTURE_ONLY_DIRS
        ):
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


TREND_FIELDS = (
    "skill_id", "snapshot_date", "research_velocity", "labor_decay", "labor_decay_source_note",
    "automation_exposure", "velocity_moderate", "velocity_fast", "direction_moderate",
    "direction_fast",
)  # fmt: skip


def load_trend_exports(conn: psycopg.Connection) -> None:
    """Load the dated, scored trend snapshots exported by the M1 pipeline
    (`src/data/seed/mock_trends_<date>.json`, written by export_fixtures_from_db.py) into
    `trend_snapshots`, preserving replay/observation/retrieval provenance as columns.
    Existing scores are never overwritten. Unknown provenance is repaired only
    when every stored score/source field matches the cited export."""
    for path in sorted(SEED.glob("mock_trends_????-??-??.json")):
        with conn.transaction():
            _load_trend_export(conn, path)


def _matches_trend_export(existing: list[dict], items: list[dict]) -> bool:
    """Compare all existing evidence, including IDs, source notes and directions.

    Numeric columns are PostgreSQL REAL: compare their exact float32 encodings,
    allowing only storage representation rounding, not a general score tolerance.
    """
    expected = {item["skill_id"]: item for item in items}
    numeric = {
        "research_velocity",
        "labor_decay",
        "automation_exposure",
        "velocity_moderate",
        "velocity_fast",
    }
    return all(
        row["skill_id"] in expected
        and all(
            struct.pack("!f", row[field]) == struct.pack("!f", expected[row["skill_id"]][field])
            if field in numeric
            else row[field] == expected[row["skill_id"]][field]
            for field in TREND_FIELDS
            if field != "snapshot_date"
        )
        for row in existing
    )


def _load_trend_export(conn: psycopg.Connection, path: Path) -> None:
    export = json.loads(path.read_text(encoding="utf-8"))
    meta = export["meta"]
    day = meta["snapshot_date"]
    provenance = provenance_values(meta, meta.get("data_provenance_note"))
    lock_snapshot(conn, day)
    previous = conn.execute(
        "SELECT is_replay FROM trend_snapshot_meta WHERE snapshot_date = %s FOR UPDATE",
        (day,),
    ).fetchone()
    if previous and previous[0] is not None and previous[0] != provenance["is_replay"]:
        raise ValueError("Cannot import replay data into a published live snapshot slot")
    if previous and previous[0] is not None:
        # A dated, classified publication is immutable; seeding is not a rescore.
        return
    with conn.cursor(row_factory=dict_row) as cur:
        existing = cur.execute(
            "SELECT * FROM trend_snapshots WHERE snapshot_date = %s FOR UPDATE", (day,)
        ).fetchall()
    if not _matches_trend_export(existing, export["items"]) or any(
        row["is_replay"] is not None and provenance_values(row) != provenance for row in existing
    ):
        # A date/NULL origin is not evidence of a fixture match. Leave the entire
        # snapshot unmodified, including metadata and any absent fixture skills.
        print(f"{path.name}: kept unmatched stored snapshot {day} unverified")
        return
    fields = (*TREND_FIELDS, *PROVENANCE_FIELDS)
    rows = [
        tuple(item.get(f, day) for f in TREND_FIELDS)
        + tuple(provenance[f] for f in PROVENANCE_FIELDS)
        for item in export["items"]
    ]
    cols = sql.SQL(", ").join(map(sql.Identifier, fields))
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(f), sql.Identifier(f))
        for f in PROVENANCE_FIELDS
    )
    query = sql.SQL(
        "INSERT INTO trend_snapshots ({}) VALUES ({}) ON CONFLICT (skill_id, snapshot_date) "
        "DO UPDATE SET {} WHERE trend_snapshots.is_replay IS NULL"
    ).format(cols, sql.SQL(", ").join(sql.Placeholder() * len(fields)), assignments)
    with conn.cursor() as cur:
        cur.executemany(query, rows)
    metadata_fields = ("snapshot_date", "sources", "provenance_note", *PROVENANCE_FIELDS)
    conn.execute(
        sql.SQL(
            "INSERT INTO trend_snapshot_meta ({}) VALUES ({}) "
            "ON CONFLICT (snapshot_date) DO UPDATE SET {} "
            "WHERE trend_snapshot_meta.is_replay IS NULL"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, metadata_fields)),
            sql.SQL(", ").join(sql.Placeholder() * len(metadata_fields)),
            sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(f), sql.Identifier(f))
                for f in metadata_fields[1:]
            ),
        ),
        (
            day,
            Jsonb(meta["sources"]),
            meta.get("data_provenance_note") or "",
            *(provenance[f] for f in PROVENANCE_FIELDS),
        ),
    )
    print(f"{path.name}: {len(rows)} trend row(s) for {day}")


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
                if table in REFERENCE_KEYS:
                    keys = REFERENCE_KEYS[table]
                    updates = [c for c in header if c not in keys]
                    query = sql.SQL(
                        "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}"
                    ).format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(map(sql.Identifier, header)),
                        sql.SQL(", ").join(sql.Placeholder() * len(header)),
                        sql.SQL(", ").join(map(sql.Identifier, keys)),
                        sql.SQL(", ").join(
                            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                            for c in updates
                        ),
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
        load_trend_exports(conn)
    print("seed done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
