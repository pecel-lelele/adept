"""Check the scheduled job's database before fetching papers or paying for inference."""

from __future__ import annotations

import os
import sys

import psycopg
from psycopg.conninfo import conninfo_to_dict


class DatabasePreflightError(RuntimeError):
    """A safe-to-log failure that contains no database credentials."""


def check_database(database_url: str) -> None:
    if not database_url.strip():
        raise DatabasePreflightError("Set the TREND_DATABASE_URL repository secret.")
    try:
        hosts = conninfo_to_dict(database_url).get("host", "").split(",")
        if any(host.strip().lower() == "helium" for host in hosts):
            raise DatabasePreflightError(
                "TREND_DATABASE_URL points to Replit's private Helium development database. "
                "Use the published app's production database connection string, reachable "
                "from GitHub Actions, or run the pipeline inside Replit."
            )
        with psycopg.connect(
            database_url, connect_timeout=10, options="-c statement_timeout=10000"
        ) as conn:
            conn.execute("SELECT 1")
    except (psycopg.Error, ValueError):
        raise DatabasePreflightError(
            "Cannot connect to the trend database. Check TREND_DATABASE_URL, external "
            "network access, credentials and SSL settings. No ingestion or RunPod "
            "inference has started."
        ) from None


def main() -> int:
    try:
        check_database(os.environ.get("DATABASE_URL", ""))
    except DatabasePreflightError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print("Trend database connection verified; ingestion may start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
