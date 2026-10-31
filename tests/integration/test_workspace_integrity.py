"""Real PostgreSQL constraints and RLS, opt-in only on an explicitly selected test database."""

import os

import psycopg
import pytest
from psycopg.rows import dict_row

from app.features.org.funding_store import ledger_scope

URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires an explicitly selected disposable DB")


def test_funding_rls_denies_unscoped_and_cross_org_reads_even_for_owner() -> None:
    with psycopg.connect(URL, row_factory=dict_row) as conn, conn.transaction(force_rollback=True):
        conn.execute(
            "INSERT INTO organizations(id,type,name) VALUES "
            "('rls-a','company','Synthetic A'), ('rls-b','company','Synthetic B')"
        )
        conn.execute("INSERT INTO learning_funding(org_id) VALUES ('rls-a'), ('rls-b')")
        conn.execute("CREATE ROLE synthetic_ledger_owner NOLOGIN NOSUPERUSER NOBYPASSRLS")
        conn.execute("ALTER TABLE learning_funding OWNER TO synthetic_ledger_owner")
        conn.execute("SET LOCAL ROLE synthetic_ledger_owner")
        assert conn.execute("SELECT * FROM learning_funding").fetchall() == []
        with ledger_scope(conn, "rls-a"):
            assert [r["org_id"] for r in conn.execute("SELECT org_id FROM learning_funding")] == [
                "rls-a"
            ]
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute("UPDATE learning_funding SET org_id='rls-b' WHERE org_id='rls-a'")
        assert conn.execute("SELECT * FROM learning_funding").fetchall() == []


def test_new_learning_rows_require_real_roles_and_workspace_organisations() -> None:
    with psycopg.connect(URL, row_factory=dict_row) as conn, conn.transaction(force_rollback=True):
        conn.execute(
            "INSERT INTO users(id,display_name) VALUES ('integrity-user','Synthetic User')"
        )
        course = conn.execute("SELECT id FROM courses LIMIT 1").fetchone()["id"]
        role = conn.execute("SELECT id FROM roles LIMIT 1").fetchone()["id"]
        for scope, target in [("personal", "missing-role"), ("org:missing-org", role)]:
            with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
                conn.execute(
                    "INSERT INTO course_progress(user_id,scope,role_id,course_id,status) "
                    "VALUES (%s,%s,%s,%s,'completed')",
                    ("integrity-user", scope, target, course),
                )
        conn.execute(
            "INSERT INTO course_progress(user_id,scope,role_id,course_id,status) "
            "VALUES (%s,'personal',%s,%s,'completed')",
            ("integrity-user", role, course),
        )
