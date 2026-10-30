"""Small-cohort suppression counts only consenting members with usable completed profiles."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.features.org import repository, service


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_threshold_suppresses_cells_and_row_aggregates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
) -> None:
    source = service.member_learners("org-demo-bank")["aisyah"]
    monkeypatch.setattr(
        service, "member_learners", lambda _org: {f"synthetic-{i}": source for i in range(count)}
    )
    monkeypatch.setattr(get_settings(), "org_min_cohort", 3)
    response = client.get("/api/v1/org/gaps", headers={"X-Demo-User": "demo-company"})
    assert response.status_code == 200
    body = response.json()
    assert body["cohort_size"] == count and body["min_cohort"] == 3
    assert body["cells"] and body["role_gaps"]
    assert all(c["suppressed"] == (count < 3) for c in body["cells"])
    assert all((c["gap"] is None) == (count < 3) for c in body["cells"])
    assert all(value == (count < 3) for value in body["role_suppressed"].values())
    assert all((value is None) == (count < 3) for value in body["role_gaps"].values())


def test_sharing_and_completed_profiles_define_the_cohort(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = repository._members["org-demo-bank"]
    assert len(service.member_learners("org-demo-bank")) == 2
    monkeypatch.setitem(
        repository._members,
        "org-demo-bank",
        [
            m.model_copy(update={"skills_shared": False}) if m.id == "aisyah" else m
            for m in original
        ],
    )
    body = client.get("/api/v1/org/gaps", headers={"X-Demo-User": "demo-company"}).json()
    assert body["cohort_size"] == 1  # invited/in-progress members never fill the threshold
    assert all(c["gap"] is None and c["suppressed"] for c in body["cells"])


def test_configured_minimum_is_enforced(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "org_min_cohort", 2)
    body = client.get("/api/v1/org/gaps", headers={"X-Demo-User": "demo-company"}).json()
    assert body["cohort_size"] == body["min_cohort"] == 2
    assert all(c["gap"] is not None and not c["suppressed"] for c in body["cells"])
