"""Exercise partial-read persistence against PostgreSQL in an isolated test schema."""

import os
import uuid
from datetime import date
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from pipelines.jobs import run

PG_URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL, reason="ADEPT_TEST_DATABASE_URL not set")
MIGRATIONS = Path(__file__).resolve().parents[3] / "src/db/migrations"
PARTIAL_MIGRATION = MIGRATIONS / "20261024010000_jobs_partial_fetch_status.sql"


def test_partial_fetch_commits_other_boards_and_migration_reverses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date(2026, 10, 24)
    schema = f"test_job_refresh_{uuid.uuid4().hex}"
    connect = psycopg.connect
    with connect(PG_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("CREATE TABLE roles (id text PRIMARY KEY)")
            original = (MIGRATIONS / "20261023160000_jobs_openings_certifications.sql").read_text()
            conn.execute(original.split("-- migrate:down")[0].replace("-- migrate:up", ""))
            migration = PARTIAL_MIGRATION.read_text()
            up, down = migration.split("-- migrate:down")
            conn.execute(up.replace("-- migrate:up", ""))
            for source, board in (("himalayas", "partial"), ("greenhouse", "complete")):
                conn.execute(
                    "INSERT INTO job_postings "
                    "(id, source, board, source_name, employer, title, url, api_url, "
                    "first_seen, last_seen) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        board,
                        source,
                        board,
                        source,
                        "Synthetic employer",
                        "Data Analyst",
                        "https://example.test/job",
                        "https://example.test/feed",
                        today,
                        today,
                    ),
                )
            monkeypatch.setenv("DATABASE_URL", PG_URL)

            def isolated_connect(url: str) -> psycopg.Connection:
                return connect(url, options=f"-c search_path={schema}")

            monkeypatch.setattr(psycopg, "connect", isolated_connect)
            run.to_db(
                [],
                [],
                [
                    {
                        "source": "himalayas",
                        "board": "partial",
                        "status": "partial",
                        "kept": 0,
                        "detail": "rate limited",
                    },
                    {"source": "greenhouse", "board": "complete", "status": "ok", "kept": 0},
                ],
                today,
            )
            assert dict(conn.execute("SELECT id, active FROM job_postings")) == {
                "partial": True,
                "complete": False,
            }
            assert dict(conn.execute("SELECT board, status FROM job_fetch_log")) == {
                "partial": "partial",
                "complete": "ok",
            }
            conn.execute(down)
            assert conn.execute(
                "SELECT status, kept, detail FROM job_fetch_log WHERE board = 'partial'"
            ).fetchone() == ("error", 0, "Partial read: rate limited")
            conn.execute(up.replace("-- migrate:up", ""))
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
