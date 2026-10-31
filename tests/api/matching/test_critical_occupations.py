from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import TextIO

import pytest
from fastapi.testclient import TestClient

from app.core import refdata
from app.features.matching import critical_occupations
from app.features.matching.critical_occupations import badge_for_role


@pytest.fixture(autouse=True)
def _fresh_reference_index() -> Iterator[None]:
    critical_occupations._reference_index.cache_clear()
    yield
    critical_occupations._reference_index.cache_clear()


def test_repeated_role_lookups_read_each_reference_file_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_open = Path.open
    opened: list[str] = []

    def count_open(path: Path, *args: object, **kwargs: object) -> TextIO:
        if path.parent == critical_occupations.REFERENCE:
            opened.append(path.name)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", count_open)
    # Unreviewed roles also use the index, without repeatedly opening the crosswalk.
    for scenario in ("moderate", "fast"):
        for _ in range(10):
            assert badge_for_role("unknown", scenario) is None
            assert badge_for_role("data-engineer", scenario) is None
            assert badge_for_role("data-analyst", scenario) is not None
    assert sorted(opened) == [
        "critical-occupation-roles.csv",
        "critical-occupations.csv",
        "critical-occupations.provenance.json",
    ]


def test_cached_reference_keeps_response_metadata_independent() -> None:
    moderate = badge_for_role("data-analyst", "moderate")
    fast = badge_for_role("data-analyst", "fast")
    assert moderate is not None and fast is not None
    assert moderate.meta.scenario == "moderate"
    assert fast.meta.scenario == "fast"
    assert moderate.meta.snapshot_date == fast.meta.snapshot_date == date(2026, 10, 29)
    expected_sources = fast.meta.model_dump()["sources"]
    moderate.meta.sources[0].name = "Mutated response"
    fast.meta.sources.clear()
    subsequent = badge_for_role("data-analyst", "moderate")
    assert subsequent is not None
    assert subsequent.meta.model_dump()["sources"] == expected_sources


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_badge_uses_reviewed_stored_id_only(client: TestClient, scenario: str) -> None:
    matches = client.get("/api/v1/matches", params={"scenario": scenario}).json()["matches"]
    supported = [m for m in matches if m["critical_occupation"]]
    assert [m["role_id"] for m in supported] == ["data-analyst"]
    badge = supported[0]["critical_occupation"]
    assert badge["masco4d"] == "2524"
    assert badge["matched_title"] == "Data Analyst"
    assert badge["meta"]["snapshot_date"] == "2026-10-29"
    assert badge["meta"]["is_estimate"] is False
    detail = client.get("/api/v1/matches/data-analyst", params={"scenario": scenario})
    assert detail.status_code == 200
    assert detail.json()["critical_occupation"] == badge
    for m in matches:
        assert m["score"] == pytest.approx(sum(c["weight"] * c["value"] for c in m["components"]))


@pytest.mark.parametrize("role_id", ["unknown", "Data Analyst", "DATA-ANALYST", "data-engineer"])
def test_no_fuzzy_or_group_membership_badges(role_id: str) -> None:
    assert badge_for_role(role_id, "moderate") is None


def test_crosswalk_resolves_to_catalogue_and_retains_source_date() -> None:
    ids = {r["id"] for r in refdata.rows("taxonomy", "roles")}
    assert "data-analyst" in ids
    badge = badge_for_role("data-analyst", "fast")
    assert badge is not None
    assert badge.meta.sources[0].retrieved_at == date(2026, 10, 29)
    assert badge.meta.sources[0].url.endswith("#page=137")


def test_container_packages_the_runtime_reference() -> None:
    from app.core.config import REPO_ROOT

    dockerfile = (REPO_ROOT / "src/docker/api.Dockerfile").read_text("utf-8")
    assert "COPY docs/reference docs/reference" in dockerfile


def test_badges_do_not_change_ranking_or_scores(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.features.matching import repository

    before = client.get("/api/v1/matches").json()["matches"]
    monkeypatch.setattr(repository, "badge_for_role", lambda role_id, scenario: None)
    after = client.get("/api/v1/matches").json()["matches"]
    assert [m["role_id"] for m in before] == [m["role_id"] for m in after]
    for first, second in zip(before, after, strict=True):
        first["critical_occupation"] = None
        assert first == second
