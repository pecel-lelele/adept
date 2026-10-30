"""Automatic snapshots can be reconstructed exactly from dated stored scorer inputs."""

import threading
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest

from app.features.data_refresh import automatic_trends, measurements, repository, service
from app.features.trends import refresh
from pipelines.trends import score


def inputs() -> measurements.MeasuredInputs:
    previous, current = automatic_trends.periods(datetime.now(UTC).date())
    ids = sorted(row["id"] for row in measurements.refdata.rows("taxonomy", "skills"))
    return measurements.MeasuredInputs(
        previous=previous,
        current=current,
        fetched=datetime.now(UTC).date(),
        counts_before={sid: 1 for sid in ids},
        counts_after={sid: 2 for sid in ids},
        total_before=200,
        total_after=200,
        skill_ids=ids,
        labor_decay=score.load_labor_decay(),
        automation_exposure=score.load_automation_exposure(),
        sample=[],
        sources=[
            {
                "name": "Synthetic test measurement",
                "url": "https://example.test/source",
                "retrieved_at": "2026-10-30",
            }
        ],
        note=f"Observed arXiv submissions {current[0]}..{current[1]}; synthetic test inputs.",
    )


def test_stored_counts_rebuild_identical_scores_without_network_or_paid_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = inputs()
    restored = measurements.MeasuredInputs.model_validate(record.model_dump(mode="json"))
    assert measurements.rows(restored) == measurements.rows(record)
    published = []

    @contextmanager
    def writer(deadline: float) -> Any:
        yield SimpleNamespace(execute=lambda *args: None)

    monkeypatch.setattr(measurements, "load", lambda *a, **k: restored)
    monkeypatch.setattr(repository, "write_connection", writer)
    monkeypatch.setattr(refresh, "latest_published", lambda *a: None)
    monkeypatch.setattr(automatic_trends, "RunPodEncoder", lambda *a, **k: pytest.fail("paid call"))
    monkeypatch.setattr(automatic_trends, "fetch_window", lambda *a: pytest.fail("network fetch"))
    monkeypatch.setattr(
        measurements.pipeline,
        "publish",
        lambda rows, day, sources, note, url, **kw: published.append((rows, day, sources)),
    )
    result = automatic_trends.run(time.monotonic(), 60, threading.Event())
    assert result.rows_upserted == len(measurements.rows(record))
    assert published[0][0] == measurements.rows(record) and published[0][1] == record.current[1]
    assert published[0][2][0]["retrieved_at"] == "2026-10-30"  # not re-dated on reconstruction


def test_legacy_rescore_can_rebuild_an_automatic_week_with_no_legacy_daily_rows(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    record = inputs()
    saved = []

    @contextmanager
    def writer(deadline: float) -> Any:
        yield object()

    monkeypatch.setattr(measurements, "load", lambda *a, **k: record)
    monkeypatch.setattr(measurements, "publish", lambda conn, value, rows: saved.append(value))
    monkeypatch.setattr(repository, "write_connection", writer)
    monkeypatch.setattr(refresh, "latest_published", lambda *a: None)
    result = refresh._rescore(
        None, SimpleNamespace(list_available_periods=lambda url: []), "synthetic"
    )
    assert result.status == "published" and result.snapshot_date == record.current[1]
    assert saved == [record]


def test_missing_measurement_schema_stops_before_paid_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Missing:
        def execute(self, *args: Any) -> None:
            raise psycopg.errors.UndefinedTable("Synthetic schema absence")

    @contextmanager
    def connection() -> Any:
        yield Missing()

    monkeypatch.setattr(measurements, "connection", connection)
    monkeypatch.setattr(refresh, "latest_published", lambda *a: None)
    monkeypatch.setattr(automatic_trends, "RunPodEncoder", lambda *a, **k: pytest.fail("paid call"))
    assert measurements.load() is None  # legacy compatibility before activation
    with pytest.raises(service.RefreshFailed, match="migration"):
        automatic_trends.run(time.monotonic(), 60, threading.Event())


def test_zero_row_database_read_does_not_substitute_seed_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Empty:
        def execute(self, *args: Any) -> Any:
            return SimpleNamespace(
                fetchone=lambda: {"n": 0, "fetched": date(2026, 10, 30), "as_of": None}
            )

    @contextmanager
    def connection() -> Any:
        yield Empty()

    monkeypatch.setattr(repository, "use_postgres", lambda: True)
    monkeypatch.setattr(repository, "connection", connection)
    monkeypatch.setitem(service._SEEDS, "jobs", lambda: pytest.fail("seed substituted"))
    value = service._one("jobs")
    assert value.rows == 0 and value.served_from == "database" and not value.is_fallback
    assert value.last_fetched_at == date(2026, 10, 30)


def test_empty_labour_table_describes_the_frozen_export(monkeypatch: pytest.MonkeyPatch) -> None:
    class Empty:
        def execute(self, *args: Any) -> Any:
            return SimpleNamespace(fetchone=lambda: {"n": 0, "fetched": None, "as_of": None})

    @contextmanager
    def connection() -> Any:
        yield Empty()

    monkeypatch.setattr(repository, "use_postgres", lambda: True)
    monkeypatch.setattr(repository, "connection", connection)
    value = service._one("labour")
    count, fetched, observed = service._seed_labour()
    assert count > 0 and value.rows == count
    assert value.served_from == "seed" and value.is_fallback
    assert value.last_fetched_at == fetched and value.data_as_of == observed
