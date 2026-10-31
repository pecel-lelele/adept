"""Run tests with fresh local PostgreSQL databases; never migrate the application DB.

Set ADEPT_TEST_PG_ADMIN_URL explicitly to a local PostgreSQL admin database named
postgres. The existing server needs pgvector and database/role administration rights.
This command never starts containers, loads .env or calls external models.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

ROOT = Path(__file__).resolve().parents[2]
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
TEST_NAME = re.compile(r"adept_(?:test|refresh_review)_[0-9a-f]{32}\Z")


def admin_connection(value: str) -> str:
    """Reject implicit, remote or application-database targets before connecting."""
    params = conninfo_to_dict(value)
    if params.get("host") not in LOCAL_HOSTS or params.get("dbname") != "postgres":
        raise ValueError("Use an explicit loopback admin URL whose database is postgres.")
    if params.get("hostaddr") and params["hostaddr"] not in LOCAL_HOSTS:
        raise ValueError("Remote hostaddr is not allowed.")
    return make_conninfo(value, connect_timeout=3, application_name="adept-isolated-test-admin")


def drop_created_database(admin: psycopg.Connection, name: str, created_oid: int) -> None:
    """Drop only a runner-named database with the exact OID recorded at creation."""
    if not TEST_NAME.fullmatch(name):
        raise ValueError("Refusing cleanup of an unrecognised database name.")
    row = admin.execute("SELECT oid FROM pg_database WHERE datname = %s", (name,)).fetchone()
    if row is None or row[0] != created_oid:
        raise ValueError("Database identity changed; refusing cleanup.")
    admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def isolated_environment(database_url: str, refresh_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        DATABASE_URL=database_url,
        ADEPT_TEST_DATABASE_URL=database_url,
        ADEPT_TREND_TEST_DATABASE_URL=database_url,
        ADEPT_REFRESH_TEST_DATABASE_URL=refresh_url,
        ADEPT_TEST_M3_BACKEND="csv",
        M3_BACKEND="csv",
        APP_ENV="development",
        LLM_PROVIDER="none",
        EMBEDDINGS_PROVIDER="none",
        RUNPOD_API_KEY="",
        GEMINI_API_KEY="",
        TRENDS_RUNPOD_API_KEY="",
        TRENDS_RUNPOD_ENDPOINT_ID="",
        PYTHONPATH=os.pathsep.join((str(ROOT / "src/api"), str(ROOT / "src"))),
    )
    return env


def main(args: list[str]) -> int:
    value = os.environ.get("ADEPT_TEST_PG_ADMIN_URL", "")
    if not value:
        print("Set ADEPT_TEST_PG_ADMIN_URL to the existing local server's postgres admin DB.")
        return 2
    try:
        admin_url = admin_connection(value)
    except (ValueError, psycopg.Error):
        print("Refusing target: an explicit loopback PostgreSQL admin URL to postgres is required.")
        return 2
    token = uuid4().hex
    names = (f"adept_test_{token}", f"adept_refresh_review_{token}")
    created: list[tuple[str, int]] = []
    with psycopg.connect(admin_url, autocommit=True) as admin:
        if admin.execute("SELECT current_database()").fetchone() != ("postgres",):
            raise ValueError("Connected database is not the selected postgres admin database.")
        try:
            for name in names:
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                oid = admin.execute(
                    "SELECT oid FROM pg_database WHERE datname = %s", (name,)
                ).fetchone()[0]
                created.append((name, oid))
                print(f"Created disposable database: {name}", flush=True)
            env = isolated_environment(
                make_conninfo(admin_url, dbname=names[0]),
                make_conninfo(admin_url, dbname=names[1]),
            )
            # Extensions are per database; refresh fixtures build only their own tables.
            with psycopg.connect(env["ADEPT_REFRESH_TEST_DATABASE_URL"]) as refresh:
                refresh.execute("CREATE EXTENSION IF NOT EXISTS vector")
            for script, arguments in (("migrate.py", ["up"]), ("seed.py", [])):
                subprocess.run(
                    [sys.executable, str(ROOT / "src/db" / script), *arguments],
                    cwd=ROOT,
                    env=env,
                    check=True,
                )
            with tempfile.TemporaryDirectory(prefix="adept-test-results-") as temporary:
                report = Path(temporary) / "pytest.xml"
                if args == ["--check"]:
                    env["PYTEST_ADDOPTS"] = shlex.join(
                        ["-rs", "-o", "junit_family=xunit1", f"--junitxml={report}"]
                    )
                    command = [sys.executable, str(ROOT / "src/scripts/dev.py"), "check"]
                else:
                    command = [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-rs",
                        "-o",
                        "junit_family=xunit1",
                        f"--junitxml={report}",
                        *args,
                    ]
                result = subprocess.run(command, cwd=ROOT, env=env, check=False)
                if not report.exists():
                    print("Test report was not produced; verification is incomplete.")
                    return result.returncode or 1
                skipped = list(ET.parse(report).getroot().iter("skipped"))
                if skipped:
                    print(f"PostgreSQL verification incomplete: {len(skipped)} skipped test(s).")
                    return 1
                print("PostgreSQL test report: zero skipped tests.", flush=True)
                return result.returncode
        finally:
            failures: list[str] = []
            for name, oid in reversed(created):
                try:
                    drop_created_database(admin, name, oid)
                    print(f"Removed disposable database: {name}", flush=True)
                except (ValueError, psycopg.Error):
                    failures.append(name)
            if failures:
                raise RuntimeError("Could not safely clean up: " + ", ".join(failures))


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (psycopg.Error, subprocess.CalledProcessError) as exc:
        # Connection strings stay in environment variables, never in diagnostics.
        print(f"PostgreSQL verification failed ({type(exc).__name__}).", file=sys.stderr)
        raise SystemExit(1) from None
