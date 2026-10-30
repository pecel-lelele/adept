"""Production-boundary evidence using real fields, not invented model attributes."""

import pytest
from fastapi.testclient import TestClient

from app.features.matching import repository
from app.features.profile import repository as profile_repository


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_real_profile_names_and_segments_do_not_change_matches(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    original = profile_repository.get_profile("aisyah")
    assert original is not None
    expected = None
    for name, segment in [
        ("Synthetic A", "working"),
        ("Synthetic B", "graduate"),
        ("Synthetic C", "switcher"),
    ]:
        raw = original.model_dump()
        raw.update(display_name=name, segment=segment)
        variant = type(original).model_validate(raw)
        assert variant.display_name == name and variant.segment == segment
        monkeypatch.setitem(profile_repository._store, "aisyah", variant)
        actual = client.get("/api/v1/matches", params={"scenario": scenario})
        assert actual.status_code == 200
        matches = actual.json()["matches"]
        assert matches
        if expected is None:
            expected = matches
        assert matches == expected


def test_boundary_is_sensitive_to_actual_skill_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    original = profile_repository.get_profile("aisyah")
    assert original is not None
    before = repository.load_profile("aisyah")
    variant = original.model_copy(update={"skills": []})
    monkeypatch.setitem(profile_repository._store, "aisyah", variant)
    after = repository.load_profile("aisyah")
    assert before.skills and after.skills == {}
    assert before.interests == after.interests
