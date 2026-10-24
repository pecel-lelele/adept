"""Terminate only this test's pooled sessions on an explicitly opted-in test database."""

import os
import uuid
from collections.abc import Iterator
from contextlib import ExitStack

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.pq import TransactionStatus
from psycopg_pool import ConnectionPool

from app.core import accounts, db, refdata
from app.core.config import get_settings
from app.core.security.rate_limit import PostgresCounter
from app.core.security.session import issue

PG_URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL, reason="ADEPT_TEST_DATABASE_URL not set")


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    db.close_pools()
    monkeypatch.setattr(get_settings(), "database_url", PG_URL)
    monkeypatch.setattr(get_settings(), "db_pool_max", 3)
    monkeypatch.setattr(get_settings(), "m3_backend", "postgres")
    refdata.invalidate()
    yield
    db.close_pools()
    refdata.invalidate()


def _terminate_idle(pool: ConnectionPool, count: int = 3) -> set[int]:
    with ExitStack() as stack:
        connections = [stack.enter_context(pool.connection()) for _ in range(count)]
        pids = {conn.info.backend_pid for conn in connections}
    with psycopg.connect(PG_URL, autocommit=True) as admin:
        for pid in pids:
            assert admin.execute("SELECT pg_terminate_backend(%s, 1000)", (pid,)).fetchone()[0]
    return pids


def test_all_terminated_idle_connections_are_replaced_before_use(database: None) -> None:
    pids = _terminate_idle(db._pool(PG_URL))
    with ExitStack() as stack:
        connections = [stack.enter_context(db.connection()) for _ in range(3)]
        for conn in connections:
            assert conn.info.backend_pid not in pids
            assert conn.info.transaction_status == TransactionStatus.IDLE
            assert conn.execute("SELECT 1 AS value").fetchone() == {"value": 1}


def test_session_and_roles_recover_without_seed_fallback(
    database: None, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    user_id = f"recovery-{uuid.uuid4().hex}"
    with psycopg.connect(PG_URL, autocommit=True) as admin:
        admin.execute(
            "INSERT INTO users (id, display_name, kind, is_synthetic) "
            "VALUES (%s, 'Synthetic Recovery Learner', 'learner', true)",
            (user_id,),
        )
        try:
            _terminate_idle(db._pool(PG_URL))
            response = client.get("/api/v1/auth/me", headers={"X-Demo-User": issue(user_id)})
            assert response.status_code == 200, response.text
            assert response.json()["id"] == user_id
            _terminate_idle(db._pool(PG_URL))
            assert refdata.rows("taxonomy", "roles")
            assert "using seed files" not in caplog.text
            assert "account lookup failed" not in caplog.text
        finally:
            admin.execute("DELETE FROM users WHERE id = %s", (user_id,))
            accounts.forget(user_id)


def test_connection_lost_during_transaction_is_not_replayed(database: None) -> None:
    attempts = 0
    with pytest.raises(psycopg.OperationalError):
        with db.connection() as conn:
            attempts += 1
            conn.execute("SELECT pg_terminate_backend(pg_backend_pid())")
    assert attempts == 1
    with db.connection() as conn:
        assert conn.execute("SELECT 1 AS value").fetchone() == {"value": 1}


def test_rate_limiter_replaces_dead_sessions_and_keeps_shared_count(database: None) -> None:
    counter = PostgresCounter(PG_URL, {}, (1, 60), clock=lambda: 1_000_020.0)
    client = f"recovery-{uuid.uuid4().hex}"
    try:
        assert counter.hit(client, "/x")[0]
        _terminate_idle(counter._conn_pool())
        assert not counter.hit(client, "/x")[0]
        assert len(counter.fallback) == 0, "a stale session must not reset the shared allowance"
    finally:
        counter.pool.close()
        with psycopg.connect(PG_URL, autocommit=True) as admin:
            admin.execute("DELETE FROM rate_limit_counters WHERE client = %s", (client,))


def test_rate_limiter_lock_timeout_falls_back_then_recovers(database: None) -> None:
    counter = PostgresCounter(PG_URL, {}, (1, 60), clock=lambda: 1_000_020.0)
    client = f"recovery-{uuid.uuid4().hex}"
    try:
        assert counter.hit(client, "/x")[0]
        with psycopg.connect(PG_URL) as blocker:
            blocker.execute(
                "SELECT * FROM rate_limit_counters WHERE client = %s FOR UPDATE", (client,)
            )
            assert counter.hit(client, "/x")[0]
            assert not counter.hit(client, "/x")[0]
            assert len(counter.fallback) == 1
        assert not counter.hit(client, "/x")[0]
        with counter.pool.connection() as conn:
            assert conn.execute("SHOW statement_timeout").fetchone() == ("2s",)
            assert conn.execute("SHOW lock_timeout").fetchone() == ("1s",)
    finally:
        counter.pool.close()
        with psycopg.connect(PG_URL, autocommit=True) as admin:
            admin.execute("DELETE FROM rate_limit_counters WHERE client = %s", (client,))
