"""Team completion counts obey sharing, workspace boundaries and per-skill suppression."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import BANK, accept_work_plan

from app.contracts.org import Member
from app.contracts.pathway import CompletionEvidence
from app.features.org import repository as org_repository
from app.features.pathway import repository
from app.features.profile import repository as profiles

HR = {"X-Demo-User": "demo-company", "X-Workspace": BANK}


def test_learning_counts_only_shared_work_records_and_revocation_suppresses(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository.reset()
    ids = ["aisyah", "emp-002", "synthetic-cohort-third"]
    members = [
        Member(
            id=uid,
            display_name="Synthetic learner",
            current_role_id=None,
            intake_status="complete",
            skills_shared=True,
        )
        for uid in ids
    ]
    monkeypatch.setitem(org_repository._members, BANK, members)
    source = profiles._store["aisyah"]
    for uid in ids:
        monkeypatch.setitem(profiles._store, uid, source.model_copy(update={"user_id": uid}))
    plans = [accept_work_plan("data-analyst", uid) for uid in ids]
    step = next(s for s in plans[0].steps if s.courses)
    course = step.courses[0]
    for uid in ids:
        # Neither personal self-reports nor other employers' completions are team records.
        for scope in [repository.PERSONAL, repository.org_scope("synthetic-other-employer")]:
            repository.set_course_status(uid, "data-analyst", course.id, "completed", course, scope)

    def row() -> dict:
        response = client.get("/api/v1/org/gaps", headers=HR)
        assert response.status_code == 200, response.text
        return next(
            r for r in response.json()["learning_progress"] if r["skill_id"] == step.skill_id
        )

    before = row()
    assert before["cohort_size"] == 3 and not before["suppressed"]
    assert before["completed_courses"] == 0 and before["planned_courses"] >= 3
    for uid in ids:
        repository.set_course_status(
            uid, "data-analyst", course.id, "completed", course, repository.org_scope(BANK)
        )
    assert row()["completed_courses"] == 3
    repository.save_evidence(
        "aisyah",
        CompletionEvidence(
            role_id="data-analyst",
            course_id=course.id,
            kind="org_rejected",
            submitted_at=datetime.now(UTC),
            scope=repository.org_scope(BANK),
        ),
    )
    assert row()["completed_courses"] == 2
    monkeypatch.setitem(
        org_repository._members,
        BANK,
        [m.model_copy(update={"skills_shared": False}) if m.id == "aisyah" else m for m in members],
    )
    hidden = row()
    assert hidden["cohort_size"] == 2 and hidden["suppressed"]
    assert hidden["completed_courses"] is None and hidden["planned_courses"] is None
    assert client.get("/api/v1/org/gaps", headers={"X-Demo-User": "aisyah"}).status_code == 403
