"""Plans, progress and badges persist in PostgreSQL (M3_BACKEND=postgres).

Skipped locally unless ADEPT_TEST_DATABASE_URL points at a migrated and seeded database;
the CI `database` job runs them on pgvector/pg16.
"""

import pytest
from fastapi.testclient import TestClient

from app.contracts.pathway import Progress, ReplanStatus, SavedPlan
from app.core.config import get_settings
from app.features.pathway import repository

ROLE = "process-automation-analyst"
pytestmark = pytest.mark.usefixtures("pg_backend")


def test_saved_plan_survives_a_new_store(client: TestClient) -> None:
    saved = SavedPlan.model_validate(
        client.post("/api/v1/pathway/plans", json={"role_id": ROLE}).json()
    )
    # A fresh store object (as after an API restart) reads the same plan back.
    again = repository.PostgresStore().get_plan("aisyah")
    assert again is not None and again.pathway == saved.pathway
    status = ReplanStatus.model_validate(client.get("/api/v1/pathway/plans/me").json())
    assert status.saved and status.saved.role_id == ROLE


def test_progress_and_badges_persist(client: TestClient) -> None:
    plan = SavedPlan.model_validate(
        client.post("/api/v1/pathway/plans", json={"role_id": ROLE}).json()
    ).pathway
    course = plan.steps[0].courses[0].id
    body = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course, "status": "completed"},
    )
    assert body.status_code == 200, body.text
    fresh = repository.PostgresStore()
    assert fresh.course_status("aisyah", ROLE) == {course: "completed"}
    progress = Progress.model_validate(
        client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    )
    assert "milestone:first" in {b.id for b in progress.badges}
    client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course, "status": "not_started"},
    )
    assert fresh.course_status("aisyah", ROLE) == {}


def test_new_authenticated_user_gets_a_user_row(client: TestClient) -> None:
    store = repository.PostgresStore()
    store.set_course_status("supabase-user-xyz", ROLE, "mslearn-pad-start", "in_progress")
    assert store.course_status("supabase-user-xyz", ROLE) == {"mslearn-pad-start": "in_progress"}


def test_unreachable_database_fails_loudly_on_write(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as m:  # undone before the fixture cleans the real database
        m.setattr(
            get_settings(),
            "database_url",
            "postgresql://nobody:x@127.0.0.1:1/none?connect_timeout=1",
        )
        resp = client.post("/api/v1/pathway/plans", json={"role_id": ROLE})
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "storage_unavailable"


def test_evidence_and_review_persist(client: TestClient) -> None:
    plan = SavedPlan.model_validate(
        client.post("/api/v1/pathway/plans", json={"role_id": ROLE}).json()
    ).pathway
    course = plan.steps[0].courses[0].id
    client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course, "status": "completed"},
    )
    fresh = repository.PostgresStore()
    assert fresh.evidence("aisyah", ROLE)[course].kind == "self_reported"
    decision = {
        "user_id": "aisyah",
        "role_id": ROLE,
        "course_id": course,
        "decision": "confirm",
        "submitted_at": fresh.evidence("aisyah", ROLE)[course].submitted_at.isoformat(),
    }
    resp = client.post(
        "/api/v1/pathway/verifications", json=decision, headers={"X-Demo-User": "demo-company"}
    )
    assert resp.status_code == 200, resp.text
    stored = repository.PostgresStore().evidence("aisyah", ROLE)[course]
    assert stored.kind == "org_confirmed" and stored.reviewed_by == "demo-company"
    assert ("aisyah", ROLE, course, "completed") in fresh.progress_of(["aisyah"])
