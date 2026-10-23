"""Reject unusable database configuration before the job invokes paid inference."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg
import pytest

from pipelines.trends import preflight


def test_missing_secret_fails_without_connecting(monkeypatch, capsys) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with patch.object(preflight.psycopg, "connect") as connect:
        assert preflight.main() == 1
    connect.assert_not_called()
    assert "TREND_DATABASE_URL" in capsys.readouterr().err


@pytest.mark.parametrize("host", ["helium", "HELIUM", "helium,db.example.test"])
def test_helium_is_rejected_without_connecting(host: str) -> None:
    with patch.object(preflight.psycopg, "connect") as connect:
        with pytest.raises(preflight.DatabasePreflightError, match="production database"):
            preflight.check_database(f"postgresql://worker:secret@{host}/adept")
    connect.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [psycopg.OperationalError("password=super-secret"), ValueError("super-secret")],
)
def test_connection_failure_is_sanitized(failure: Exception, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://worker:super-secret@db.example.test/adept")
    with patch.object(preflight.psycopg, "connect", side_effect=failure):
        assert preflight.main() == 1
    error = capsys.readouterr().err
    assert "No ingestion or RunPod inference has started" in error
    assert "super-secret" not in error
    assert "postgresql://" not in error


def test_success_checks_database_with_bounded_timeouts(monkeypatch, capsys) -> None:
    database_url = "postgresql://worker:secret@db.example.test/adept?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", database_url)
    connection = MagicMock()
    with patch.object(preflight.psycopg, "connect", return_value=connection) as connect:
        assert preflight.main() == 0
    connect.assert_called_once_with(
        database_url, connect_timeout=10, options="-c statement_timeout=10000"
    )
    connection.__enter__.return_value.execute.assert_called_once_with("SELECT 1")
    assert not capsys.readouterr().err


def test_malformed_connection_string_is_sanitized() -> None:
    with patch.object(preflight.psycopg, "connect") as connect:
        with pytest.raises(preflight.DatabasePreflightError) as error:
            preflight.check_database("password=super-secret invalid-connection-string")
    connect.assert_not_called()
    assert "super-secret" not in str(error.value)
