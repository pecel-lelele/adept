"""Explicit failure inputs for trend unit tests, independent of integration opt-ins."""

import psycopg
import pytest

from app.features.trends import repository


@pytest.fixture
def unavailable_trend_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(**kwargs: object) -> None:
        raise psycopg.OperationalError("Synthetic trend database outage")

    monkeypatch.setattr(repository, "_get_connection", unavailable)
