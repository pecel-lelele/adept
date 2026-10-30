"""Internal strict callers must never mistake database failures for fixture data."""

import socket
import struct
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from app.core.errors import NotFoundError
from app.features.trends import mocks, repository, service
from app.features.trends.repository import TrendsUnavailableError

DAY = date(2026, 10, 20)
ERRORS = [
    psycopg.OperationalError("connection timeout expired"),
    psycopg.errors.QueryCanceled("canceling statement due to statement timeout"),
    psycopg.errors.LockNotAvailable("canceling statement due to lock timeout"),
]


@pytest.fixture(autouse=True)
def reset_cache() -> Iterator[None]:
    repository._reset_db_cache()
    yield
    repository._reset_db_cache()


def connection() -> tuple[MagicMock, MagicMock]:
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    row = mocks.snapshot("moderate", DAY).items[0].model_dump()

    def execute(query: str, params: object = None) -> None:
        cur.fetchall.return_value = [{"snapshot_date": DAY}] if "DISTINCT" in query else [row]

    cur.execute.side_effect = execute
    return conn, cur


@pytest.mark.parametrize("error", ERRORS)
def test_resolution_failure_defaults_to_fixture_but_strict_raises(error: Exception) -> None:
    conn, cur = connection()
    with patch("psycopg.connect", return_value=conn) as connect:
        if isinstance(error, psycopg.errors.QueryCanceled | psycopg.errors.LockNotAvailable):
            cur.execute.side_effect = error
        else:
            connect.side_effect = error
        assert service.get_snapshot(DAY, "moderate") == mocks.snapshot("moderate", DAY)
        # Retry while the demo negative cache is active: strict must still fail closed.
        with patch.object(mocks, "snapshot") as fixture:
            with pytest.raises(TrendsUnavailableError) as caught:
                service.get_snapshot(DAY, "moderate", strict=True)
            assert caught.value.__cause__ is error
            fixture.assert_not_called()
        if connect.side_effect is None:
            assert conn.close.call_count == 2


@pytest.mark.parametrize("error", ERRORS)
def test_snapshot_read_failure_serves_disclosed_fallback_but_strict_raises(
    error: Exception,
) -> None:
    conn, cur = connection()
    execute = cur.execute.side_effect

    def fail_on_rows(query: str, params: object = None) -> None:
        if "SELECT ts.*" in query:
            raise error
        execute(query, params)

    cur.execute.side_effect = fail_on_rows
    with (
        patch("psycopg.connect", return_value=conn),
        patch.object(mocks, "snapshot", wraps=mocks.snapshot) as fixture,
    ):
        snap = service.get_snapshot(DAY, "moderate")
        assert snap.meta.snapshot_date == DAY
        assert snap.meta.is_fallback and snap.meta.served_from == "fixture"
        with pytest.raises(TrendsUnavailableError) as caught:
            service.get_snapshot(DAY, "moderate", strict=True)
        assert caught.value.__cause__ is error
        fixture.assert_called_once_with("moderate", DAY)
        assert conn.close.call_count == 2


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_strict_success_identical_to_default(scenario: str) -> None:
    conn, _ = connection()
    with patch("psycopg.connect", return_value=conn) as connect:
        normal = service.get_snapshot(DAY, scenario)
        strict = service.get_snapshot(DAY, scenario, strict=True)
        assert strict.model_dump_json() == normal.model_dump_json()
        assert connect.call_count == 2
        for call in connect.call_args_list:
            assert call.kwargs["connect_timeout"] == 2
            assert call.kwargs["options"] == "-c statement_timeout=2000 -c lock_timeout=1000"


@pytest.mark.parametrize("error", ERRORS)
def test_standalone_loaders_cannot_swallow_strict_failures(error: Exception) -> None:
    with patch("psycopg.connect", side_effect=error):
        assert repository._list_snapshot_dates_db() == []
        assert repository._load_snapshot_db(DAY, "moderate") is None
        with pytest.raises(TrendsUnavailableError):
            repository._list_snapshot_dates_db(strict=True)
        with pytest.raises(TrendsUnavailableError):
            repository._load_snapshot_db(DAY, "moderate", strict=True)


def test_strict_rejects_empty_database_and_existing_fixture_context() -> None:
    conn, cur = connection()
    cur.execute.side_effect = None
    cur.fetchall.return_value = []
    with patch("psycopg.connect", return_value=conn):
        assert service.get_snapshot(DAY, "moderate") == mocks.snapshot("moderate", DAY)
        with pytest.raises(TrendsUnavailableError):
            service.get_snapshot(DAY, "moderate", strict=True)
    ctx = repository.ResolvedContext("fixture", [DAY])
    with pytest.raises(TrendsUnavailableError):
        repository.get_snapshot(ctx, DAY, "moderate", strict=True)


def test_unknown_date_remains_not_found_in_strict_mode() -> None:
    conn, _ = connection()
    with patch("psycopg.connect", return_value=conn):
        with pytest.raises(NotFoundError):
            service.get_snapshot(date(1999, 1, 1), "moderate", strict=True)


@contextmanager
def silent_postgres() -> Iterator[tuple[str, Event]]:
    """Complete a real libpq handshake, then accept query bytes without replying."""
    disconnected = Event()
    errors: list[Exception] = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(8)

        def serve() -> None:
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(8)

                    def read_exact(size: int) -> bytes:
                        data = b""
                        while len(data) < size:
                            chunk = peer.recv(size - len(data))
                            if not chunk:
                                raise EOFError("Client disconnected during startup")
                            data += chunk
                        return data

                    length = struct.unpack("!I", read_exact(4))[0]
                    read_exact(length - 4)
                    # AuthenticationOk, then ReadyForQuery (idle).
                    peer.sendall(
                        b"R" + struct.pack("!II", 8, 0) + b"Z" + struct.pack("!I", 5) + b"I"
                    )
                    while peer.recv(65536):
                        pass
                    disconnected.set()
            except Exception as exc:
                errors.append(exc)

        worker = Thread(target=serve, daemon=True)
        worker.start()
        port = listener.getsockname()[1]
        try:
            yield f"postgresql://test:test@127.0.0.1:{port}/test?sslmode=disable", disconnected
        finally:
            worker.join(timeout=9)
            assert not worker.is_alive(), "Stalled socket/server worker was left running"
            assert not errors, errors


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("stage", ["dates", "snapshot", "standalone_dates", "standalone_snapshot"])
def test_established_connection_stall_is_interrupted(strict: bool, stage: str) -> None:
    with silent_postgres() as (url, disconnected):
        with patch.object(
            repository, "get_settings", return_value=SimpleNamespace(database_url=url)
        ):
            start = time.monotonic()
            if stage == "dates":
                if strict:
                    with pytest.raises(TrendsUnavailableError):
                        service.get_snapshot(DAY, "moderate", strict=True)
                else:
                    assert service.get_snapshot(DAY, "moderate") == mocks.snapshot("moderate", DAY)
            elif stage == "snapshot":
                with repository.ResolvedContext("db", [DAY], repository._get_connection()) as ctx:
                    error = TrendsUnavailableError if strict else NotFoundError
                    with pytest.raises(error):
                        repository.get_snapshot(ctx, DAY, "moderate", strict=strict)
                    assert ctx.conn.closed or ctx.conn.broken
            else:
                loader = (
                    repository._list_snapshot_dates_db
                    if stage == "standalone_dates"
                    else lambda **kw: repository._load_snapshot_db(DAY, "moderate", **kw)
                )
                if strict:
                    with pytest.raises(TrendsUnavailableError):
                        loader(strict=True)
                else:
                    assert loader() == ([] if stage == "standalone_dates" else None)
            elapsed = time.monotonic() - start
            assert 2.5 <= elapsed < 5, f"Client read was not bounded: {elapsed:.3f}s"
            assert disconnected.wait(1), "Deadline returned without stopping the pending socket I/O"


def test_successful_read_cancels_watchdog_without_disconnecting() -> None:
    first, second = socket.socketpair()
    with first, second:
        conn = SimpleNamespace(fileno=first.fileno)
        with repository._read_deadline(conn, timeout_s=0.05):
            pass
        time.sleep(0.1)
        first.sendall(b"ok")
        assert second.recv(2) == b"ok"
