"""Check the scheduled job's database before fetching papers or paying for inference."""

from __future__ import annotations

import os
import sys

import psycopg
from psycopg.conninfo import conninfo_to_dict

REQUIRED_PRIVILEGES: dict[str, tuple[str, ...]] = {
    "skills": ("SELECT",),
    "skill_signal_raw": ("SELECT", "INSERT", "UPDATE"),
    "arxiv_fetch_log": ("SELECT", "INSERT", "UPDATE"),
    "trend_snapshots": ("SELECT", "INSERT", "UPDATE", "DELETE"),
    "trend_snapshot_meta": ("SELECT", "INSERT", "UPDATE"),
}
SERIAL_TABLES = ("skill_signal_raw", "arxiv_fetch_log", "trend_snapshots")


class DatabasePreflightError(RuntimeError):
    """A safe-to-log failure that contains no database credentials."""


def check_database(database_url: str) -> None:
    if not database_url.strip():
        raise DatabasePreflightError("Set the TREND_DATABASE_URL repository secret.")
    try:
        params = conninfo_to_dict(database_url)
        hosts = params.get("host", "").split(",")
        if any(host.strip().lower() == "helium" for host in hosts):
            raise DatabasePreflightError(
                "TREND_DATABASE_URL points to Replit's private Helium development database. "
                "Use the published app's production database connection string, reachable "
                "from GitHub Actions, or run the pipeline inside Replit."
            )
        with psycopg.connect(
            database_url,
            connect_timeout=10,
            options=f"{params.get('options', '')} -c statement_timeout=10000".strip(),
        ) as conn:
            row = conn.execute("SHOW transaction_read_only").fetchone()
            if row is None or row[0] != "off":
                raise DatabasePreflightError("The trend database connection is read-only.")
            for table, privileges in REQUIRED_PRIVILEGES.items():
                for privilege in privileges:
                    row = conn.execute(
                        "SELECT has_table_privilege(to_regclass(%s), %s)", (table, privilege)
                    ).fetchone()
                    if row is None or row[0] is not True:
                        raise DatabasePreflightError(
                            f"Trend database requires a migrated {table} table and "
                            f"{privilege} permission before inference."
                        )
            for table in SERIAL_TABLES:
                row = conn.execute(
                    "SELECT has_sequence_privilege(pg_get_serial_sequence(%s, 'id'), 'USAGE') "
                    "OR has_sequence_privilege(pg_get_serial_sequence(%s, 'id'), 'UPDATE')",
                    (table, table),
                ).fetchone()
                if row is None or row[0] is not True:
                    raise DatabasePreflightError(
                        f"Trend database requires sequence access for {table} before inference."
                    )
    except (psycopg.Error, ValueError):
        raise DatabasePreflightError(
            "Cannot use the trend database. Check TREND_DATABASE_URL, external "
            "network access, credentials, SSL settings and migrations. No ingestion or RunPod "
            "inference has started."
        ) from None


def main() -> int:
    try:
        check_database(os.environ.get("DATABASE_URL", ""))
    except DatabasePreflightError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print("Trend database connection and write permissions verified; ingestion may start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
