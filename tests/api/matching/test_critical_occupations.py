from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core import refdata
from app.features.matching.critical_occupations import badge_for_role


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
