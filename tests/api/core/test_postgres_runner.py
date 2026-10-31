"""Safety checks for the opt-in disposable PostgreSQL test runner."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from psycopg.conninfo import conninfo_to_dict

from scripts.test_postgres import admin_connection, drop_created_database, isolated_environment


@pytest.mark.parametrize(
    "value",
    [
        "dbname=postgres",
        "host=example.test dbname=postgres",
        "host=127.0.0.1 dbname=adept",
        "host=127.0.0.1 hostaddr=192.0.2.1 dbname=postgres",
    ],
)
def test_admin_target_must_be_explicit_local_and_not_application_data(value: str) -> None:
    with pytest.raises(ValueError):
        admin_connection(value)


def test_admin_connection_preserves_credentials_without_returning_to_application_db() -> None:
    params = conninfo_to_dict(
        admin_connection("host=127.0.0.1 port=5433 dbname=postgres user=synthetic")
    )
    assert params["dbname"] == "postgres" and params["port"] == "5433"
    assert params["connect_timeout"] == "3"


def test_cleanup_rejects_other_names_and_replaced_databases_before_drop() -> None:
    admin = MagicMock()
    with pytest.raises(ValueError):
        drop_created_database(admin, "adept", 1)
    admin.execute.assert_not_called()
    admin.execute.return_value.fetchone.return_value = (2,)
    with pytest.raises(ValueError):
        drop_created_database(admin, "adept_test_" + "a" * 32, 1)
    assert admin.execute.call_count == 1, "identity mismatch must never execute DROP"


def test_cleanup_drops_only_verified_created_database() -> None:
    admin = MagicMock()
    name = "adept_refresh_review_" + "b" * 32
    admin.execute.return_value.fetchone.return_value = (42,)
    drop_created_database(admin, name, 42)
    assert admin.execute.call_count == 2
    query = admin.execute.call_args.args[0].as_string()
    assert query == f'DROP DATABASE "{name}" WITH (FORCE)'


def test_child_environment_selects_test_databases_and_disables_paid_providers() -> None:
    env = isolated_environment("synthetic-primary", "synthetic-refresh")
    assert env["DATABASE_URL"] == env["ADEPT_TEST_DATABASE_URL"] == "synthetic-primary"
    assert env["ADEPT_REFRESH_TEST_DATABASE_URL"] == "synthetic-refresh"
    assert env["LLM_PROVIDER"] == env["EMBEDDINGS_PROVIDER"] == "none"
    assert env["RUNPOD_API_KEY"] == env["GEMINI_API_KEY"] == ""
