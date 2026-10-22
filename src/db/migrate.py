"""Minimal migration runner for src/db/migrations/*.sql (dbmate-compatible format).

Usage (from the repo root): .venv/bin/python src/db/migrate.py [up|status]

Each file is <YYYYMMDDHHMMSS>_<name>.sql with `-- migrate:up` and `-- migrate:down`
sections. Applied versions are recorded in `schema_migrations`, the same table dbmate
uses, so the team can switch to dbmate later without re-running anything.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
ALIAS_MIGRATIONS = {
    "20261021150000_core_skill_aliases.sql",
    "20261021150000_m2_skill_aliases.sql",
}
DEFAULT_URL = "postgresql://adept:adept@127.0.0.1:5433/adept"


def up_section(sql: str) -> str:
    """Return the SQL between the `-- migrate:up` and `-- migrate:down` marker lines."""
    lines = sql.splitlines()
    stripped = [line.strip() for line in lines]
    if "-- migrate:up" not in stripped:
        raise ValueError("missing '-- migrate:up' marker line")
    start = stripped.index("-- migrate:up") + 1
    end = stripped.index("-- migrate:down") if "-- migrate:down" in stripped else len(lines)
    body = "\n".join(lines[start:end]).strip()
    if not any(s and not s.startswith("--") for s in stripped[start:end]):
        raise ValueError("'-- migrate:up' section has no statements")
    return body


def version_of(path: Path) -> str:
    version = path.name.split("_", 1)[0]
    if not (version.isdigit() and len(version) == 14):
        raise ValueError(f"{path.name}: expected <YYYYMMDDHHMMSS>_<name>.sql")
    return version


def pending(applied: set[str]) -> list[Path]:
    files = sorted(MIGRATIONS.glob("*.sql"))
    unique: dict[str, Path] = {}
    for file in files:
        version = version_of(file)
        previous = unique.get(version)
        if previous is not None:
            # Two branches independently added the same aliases column at the same
            # timestamp. Preserve both immutable files, but apply the schema once.
            # Ignore only existence guards and comments; any other collision fails.
            if {previous.name, file.name} != ALIAS_MIGRATIONS or normalized_sql(
                previous
            ) != normalized_sql(file):
                raise ValueError(
                    f"Conflicting migration version {version}: {previous.name}, {file.name}"
                )
            continue
        unique[version] = file
    return [file for version, file in unique.items() if version not in applied]


def normalized_sql(path: Path) -> str:
    sql = re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))
    sql = re.sub(r"\bIF\s+(?:NOT\s+)?EXISTS\b", "", sql, flags=re.IGNORECASE)
    return " ".join(sql.split())


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "up"
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version varchar(128) PRIMARY KEY)"
        )
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        todo = pending(applied)
        if command == "status":
            for f in sorted(MIGRATIONS.glob("*.sql")):
                state = "applied" if version_of(f) in applied else "pending"
                print(f"{state}  {f.name}")
            return 0
        if command != "up":
            print("usage: migrate.py [up|status]", file=sys.stderr)
            return 2
        for f in todo:
            print(f"applying {f.name}")
            with conn.transaction():
                conn.execute(up_section(f.read_text(encoding="utf-8")))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", [version_of(f)])
        print(f"{len(todo)} migration(s) applied")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
