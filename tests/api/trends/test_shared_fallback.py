from collections.abc import Iterator
from datetime import date
from unittest.mock import patch

import pytest

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.features.matching import trend_port as matching
from app.features.pathway import trend_port as pathway
from app.features.trends import mocks, repository, service


@pytest.fixture(autouse=True)
def clear_ports() -> Iterator[None]:
    pathway.reset_cache()
    repository._reset_db_cache()
    yield
    pathway.reset_cache()
    repository._reset_db_cache()


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("previous_db_read", [False, True])
def test_all_consumers_share_the_same_dated_fallback(
    scenario: str, previous_db_read: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    day = date(2026, 10, 27)
    good = mocks.snapshot("moderate").model_copy(deep=True)
    good.meta = good.meta.model_copy(
        update={
            "snapshot_date": day,
            "available_snapshots": [day],
            "served_from": "db",
            "is_fallback": False,
        }
    )
    if previous_db_read:
        # A real serving read populates the last-good store; no private test-only copy.
        with (
            patch.object(
                repository, "resolve_context", return_value=repository.ResolvedContext("db", [day])
            ),
            patch.object(repository, "get_snapshot", return_value=good),
        ):
            assert service.get_snapshot(None, "moderate") is good
        # Expire the response cache while retaining the last successful database read.
        with service._cache_lock:
            service._cache.clear()
    monkeypatch.setattr(get_settings(), "app_env", "production")
    with patch.object(repository, "_get_connection", side_effect=OSError("synthetic outage")):
        radar = service.get_snapshot(None, scenario)
        matches = matching.fetch_snapshot(scenario)
        plan = pathway.current(scenario)
    assert plan is not None
    expected_day = day if previous_db_read else mocks.AVAILABLE_MOCK_DATES[-1]
    expected_source = "db" if previous_db_read else "fixture"
    assert (
        radar.meta.snapshot_date
        == matches.snapshot_date
        == plan.snapshot.snapshot_date
        == expected_day
    )
    assert (
        radar.meta.served_from
        == matches.served_from
        == plan.snapshot.served_from
        == expected_source
    )
    assert radar.meta.is_fallback and matches.is_fallback and plan.snapshot.is_fallback
    assert radar.meta.scenario == scenario
    assert (
        matches.velocities
        == plan.growth
        == {item.skill_id: getattr(item, f"velocity_{scenario}") for item in radar.items}
    )
    assert plan.scenario_weighted
    for advertised in radar.meta.available_snapshots:
        assert service.last_good_snapshot(advertised, scenario).meta.snapshot_date == advertised
    assert [(s.name, s.url, s.retrieved_at) for s in radar.meta.sources] == [
        (s.name, s.url, s.retrieved_at) for s in matches.sources
    ]
    assert tuple(matches.sources) == plan.snapshot.all_sources()
    assert good.meta.is_fallback is False, (
        "fallback copies must not mark the healthy snapshot stale"
    )


def test_fallback_never_substitutes_a_different_replay_date() -> None:
    with pytest.raises(NotFoundError):
        service.last_good_snapshot(date(1999, 1, 1), "fast")


def test_last_good_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "_CACHE_MAX", 2)
    for day in (date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22)):
        good = mocks.snapshot("moderate").model_copy(deep=True)
        good.meta = good.meta.model_copy(
            update={"snapshot_date": day, "served_from": "db", "is_fallback": False}
        )
        with (
            patch.object(
                repository, "resolve_context", return_value=repository.ResolvedContext("db", [day])
            ),
            patch.object(repository, "get_snapshot", return_value=good),
        ):
            service.get_snapshot(day, "moderate")
    assert len(service._last_good) == 2
    assert service.last_good_snapshot(None, "fast").meta.snapshot_date == date(2026, 10, 22)


def test_healthy_read_replaces_fallback_without_mutating_earlier_snapshots() -> None:
    fallback = service.last_good_snapshot(None, "moderate")
    good = mocks.snapshot("moderate").model_copy(deep=True)
    day = date(2026, 10, 27)
    good.meta = good.meta.model_copy(
        update={"snapshot_date": day, "served_from": "db", "is_fallback": False}
    )
    with (
        patch.object(
            repository, "resolve_context", return_value=repository.ResolvedContext("db", [day])
        ),
        patch.object(repository, "get_snapshot", return_value=good),
    ):
        healthy = service.get_snapshot(None, "moderate")
    assert healthy.meta.is_fallback is False
    assert fallback.meta.is_fallback is True
    assert service.last_good_snapshot(None, "fast").meta.snapshot_date == day
