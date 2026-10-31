"""Target choice, durable per-role progress and the self-reported learning estimate."""

import pytest
from fastapi.testclient import TestClient

from app.contracts.pathway import Course
from app.features.pathway import repository

PERSONAL = {"X-Demo-User": "aisyah", "X-Workspace": "personal"}


@pytest.fixture(autouse=True)
def fresh_plans() -> None:
    repository.reset()


def test_choice_switching_and_undo_preserve_progress_without_changing_match_score(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/pathway/plans/me", headers=PERSONAL).json()["saved"] is None
    role = "data-analyst"
    chosen = client.post(
        "/api/v1/pathway/plans",
        headers=PERSONAL,
        json={"role_id": role, "scenario": "moderate"},
    )
    assert chosen.status_code == 200
    courses = [c for s in chosen.json()["pathway"]["steps"] for c in s["courses"]]
    assert courses
    before = client.get("/api/v1/pathway/progress", headers=PERSONAL).json()
    match = client.get(f"/api/v1/matches/{role}", headers=PERSONAL).json()["score"]
    # All self-ticked courses contribute only to the clearly labelled learning estimate.
    for course in courses:
        response = client.post(
            "/api/v1/pathway/progress",
            headers=PERSONAL,
            json={"role_id": role, "course_id": course["id"], "status": "completed"},
        )
        assert response.status_code == 200, response.text
    done = response.json()
    assert done["percent_complete"] == 1
    assert done["estimated_skill_fit"] > before["estimated_skill_fit"]
    assert client.get(f"/api/v1/matches/{role}", headers=PERSONAL).json()["score"] == match
    assert (
        client.post(
            "/api/v1/pathway/plans",
            headers=PERSONAL,
            json={"role_id": "business-analyst", "scenario": "moderate"},
        ).status_code
        == 200
    )
    previous = client.get(
        "/api/v1/pathway/progress",
        headers=PERSONAL,
        params={"role_id": role},
    ).json()
    assert previous["course_status"] == done["course_status"]
    assert previous["pathway"] == chosen.json()["pathway"]
    for course in courses:
        undone = client.post(
            "/api/v1/pathway/progress",
            headers=PERSONAL,
            json={"role_id": role, "course_id": course["id"], "status": "not_started"},
        )
        assert undone.status_code == 200
    assert undone.json()["estimated_skill_fit"] == before["estimated_skill_fit"]
    assert undone.json()["percent_complete"] == 0


def _first_course(client: TestClient, role: str) -> str:
    plan = client.get(
        "/api/v1/pathway", headers=PERSONAL, params={"role_id": role, "scenario": "moderate"}
    ).json()
    return next(s for s in plan["steps"] if s["courses"])["courses"][0]["id"]


def test_progress_updates_are_refused_for_a_role_never_chosen(client: TestClient) -> None:
    # The navigation lock is only a hint: the server enforces the explicit choice too.
    course = _first_course(client, "data-analyst")
    write = {"role_id": "data-analyst", "course_id": course, "status": "completed"}
    params = {"role_id": "data-analyst"}

    preview = client.get("/api/v1/pathway/progress", headers=PERSONAL, params=params)
    assert preview.status_code == 200 and preview.json()["trackable"] is False
    for response in (
        client.post("/api/v1/pathway/progress", headers=PERSONAL, json=write),
        client.post(
            "/api/v1/pathway/progress/evidence",
            headers=PERSONAL,
            json={
                "role_id": "data-analyst",
                "course_id": course,
                "url": "https://example.test/certificate",
            },
        ),
    ):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "role_required"
    assert repository.learning_records(["aisyah"]) == []

    # Choosing a different role does not unlock this one.
    other = {"role_id": "business-analyst", "scenario": "moderate"}
    assert client.post("/api/v1/pathway/plans", headers=PERSONAL, json=other).status_code == 200
    assert client.post("/api/v1/pathway/progress", headers=PERSONAL, json=write).status_code == 409


def test_previously_chosen_role_stays_available_in_every_scenario(client: TestClient) -> None:
    first = {"role_id": "data-analyst", "scenario": "moderate"}
    assert client.post("/api/v1/pathway/plans", headers=PERSONAL, json=first).status_code == 200
    other = {"role_id": "business-analyst", "scenario": "moderate"}
    assert client.post("/api/v1/pathway/plans", headers=PERSONAL, json=other).status_code == 200
    for scenario in ["moderate", "fast"]:
        response = client.get(
            "/api/v1/pathway/progress",
            headers=PERSONAL,
            params={"role_id": "data-analyst", "scenario": scenario},
        )
        assert response.status_code == 200, response.text
        assert response.json()["trackable"] is True


def test_existing_records_for_an_unsaved_role_stay_readable(client: TestClient) -> None:
    # Learning recorded before the lock existed must not become unreachable.
    course = _first_course(client, "data-analyst")
    plan = client.get("/api/v1/pathway", headers=PERSONAL, params={"role_id": "data-analyst"})
    facts = next(c for s in plan.json()["steps"] for c in s["courses"] if c["id"] == course)
    repository.set_course_status(
        "aisyah",
        "data-analyst",
        course,
        "completed",
        Course.model_validate(facts),
        repository.PERSONAL,
    )
    response = client.get(
        "/api/v1/pathway/progress", headers=PERSONAL, params={"role_id": "data-analyst"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["course_status"][course] == "completed"
    assert response.json()["trackable"] is True


def test_unknown_choice_cannot_save_an_invented_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/pathway/plans",
        headers=PERSONAL,
        json={"role_id": "synthetic-non-catalogue-role", "scenario": "moderate"},
    )
    assert response.status_code == 404
    assert repository.get_plan("aisyah") is None
