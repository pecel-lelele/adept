from datetime import date

import pytest

from app.core.errors import AppError
from app.features.jobs import repository, service


def test_empty_search_uses_the_stored_observation_not_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repository, "observation_date", lambda: date(2026, 10, 23))
    meta = service._meta([], "fast")
    assert meta.snapshot_date == date(2026, 10, 23)
    assert meta.sources[0].retrieved_at == date(2026, 10, 23)


def test_no_observations_cannot_claim_a_fresh_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "observation_date", lambda: None)
    with pytest.raises(AppError) as caught:
        service._meta([], "moderate")
    assert caught.value.code == "jobs_no_data"
