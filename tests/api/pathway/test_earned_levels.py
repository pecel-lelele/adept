"""H08: completed learning raises matching levels only with accepted evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.contracts.org import Member
from app.contracts.pathway import CompletionEvidence, Course, Progress, SavedPlan
from app.core.auth import CurrentUser
from app.core.db import connection
from app.features.matching import repository as matching_repository
from app.features.org import service as org_service
from app.features.pathway import data, repository
from app.features.pathway import service as pathway_service
from app.features.pathway.verification import effective_statuses
from app.main import app

NOW = datetime(2026, 10, 22, tzinfo=UTC)


@pytest.fixture
def client(request: pytest.FixtureRequest) -> TestClient:
    # Exercise real HTTP limits without consuming the shared testclient IP's allowance.
    return TestClient(app, client=(f"earned-{request.node.name}", 50000))


def _course(cid: str, skills: list[str], level: int) -> Course:
    return Course(
        id=cid,
        title=cid,
        provider="p",
        url="https://example.test/c",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 1),
        skill_ids=skills,
        level=level,
    )


def _evidence(cid: str, kind: str, link_status: str = "not_submitted") -> CompletionEvidence:
    return CompletionEvidence(
        role_id="r",
        course_id=cid,
        kind=kind,  # type: ignore[arg-type]
        link_status=link_status,  # type: ignore[arg-type]
        submitted_at=NOW,
    )


COURSES = {
    "self": _course("self", ["sql"], 3),
    "cert-ok": _course("cert-ok", ["python"], 3),
    "cert-bad": _course("cert-bad", ["excel"], 3),
    "confirmed": _course("confirmed", ["sql", "viz"], 4),
    "rejected": _course("rejected", ["ml"], 4),
    "open": _course("open", ["stats"], 3),
}


def test_only_reviewed_or_provider_checked_completions_count() -> None:
    evidence = {
        "cert-ok": _evidence("cert-ok", "certificate_link", "provider_verified"),
        "cert-bad": _evidence("cert-bad", "certificate_link", "unreachable"),
        "confirmed": _evidence("confirmed", "org_confirmed"),
        "rejected": _evidence("rejected", "org_rejected"),
    }
    raw = {cid: "completed" for cid in COURSES if cid != "open"} | {"open": "in_progress"}
    statuses = effective_statuses(raw, evidence)  # type: ignore[arg-type]
    earned = pathway_service.earned_levels(COURSES, statuses, evidence)
    assert earned == {"python": 3, "sql": 4, "viz": 4}
    # self-ticked (sql via "self"), an unreachable link, a rejection and an unfinished course
    # change nothing; the strongest level wins per skill.
    assert "excel" not in earned and "ml" not in earned and "stats" not in earned


def test_matching_uses_the_higher_of_intake_and_evidenced_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = matching_repository.load_profile("aisyah").skills
    skill = next(iter(before))
    monkeypatch.setattr(
        pathway_service, "evidenced_levels", lambda user_id: {skill: 5, "new-skill": 2}
    )
    after = matching_repository.load_profile("aisyah").skills
    assert after[skill] == 5.0
    assert after["new-skill"] == 2.0
    assert {k: v for k, v in after.items() if k not in (skill, "new-skill")} == {
        k: v for k, v in before.items() if k != skill
    }
    monkeypatch.setattr(pathway_service, "evidenced_levels", lambda user_id: {skill: 1})
    assert matching_repository.load_profile("aisyah").skills[skill] == before[skill]


ROLE = "process-automation-analyst"
LEARNER = CurrentUser(id="aisyah", display_name="Aisyah", kind="learner")


@pytest.fixture(params=["memory", "postgres"])
def learning_backend(request: pytest.FixtureRequest) -> None:
    if request.param == "postgres":
        request.getfixturevalue("pg_backend")


def _complete_and_confirm(client: TestClient) -> tuple[Course, str]:
    response = client.post("/api/v1/pathway/plans", json={"role_id": ROLE})
    assert response.status_code == 200, response.text
    plan = SavedPlan.model_validate(response.json()).pathway
    step, course = next(
        (step, course)
        for step in plan.steps
        for course in step.courses
        if course.level >= step.target_level
    )
    response = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course.id, "status": "completed"},
    )
    assert response.status_code == 200, response.text
    evidence = repository.evidence("aisyah", ROLE)[course.id]
    response = client.post(
        "/api/v1/pathway/verifications",
        json={
            "user_id": "aisyah",
            "role_id": ROLE,
            "course_id": course.id,
            "decision": "confirm",
            "submitted_at": evidence.submitted_at.isoformat(),
        },
        headers={"X-Demo-User": "demo-company"},
    )
    assert response.status_code == 200, response.text
    return course, step.skill_id


def test_target_change_and_retired_course_keep_earned_levels(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, learning_backend: None
) -> None:
    course, skill = _complete_and_confirm(client)
    before = matching_repository.load_profile("aisyah").skills
    other_role = next(role for role in data.target_role_ids() if role != ROLE)
    response = client.post("/api/v1/pathway/plans", json={"role_id": other_role})
    assert response.status_code == 200, response.text
    assert repository.get_plan("aisyah").role_id == other_role
    # The original plan has gone and the live catalogue can no longer supply this course.
    monkeypatch.setattr(data, "catalogue", lambda: [])
    assert pathway_service.evidenced_levels("aisyah")[skill] == course.level
    assert matching_repository.load_profile("aisyah").skills == before
    assert repository.course_facts("aisyah", ROLE)[course.id] == course
    assert (
        pathway_service.verification_queue(
            CurrentUser("demo-company", "Demo HR", "org_admin", "org-demo-bank")
        )
        .items[0]
        .course
        == course
    )


def test_plans_comparisons_and_team_gaps_use_the_matching_levels(
    client: TestClient, learning_backend: None
) -> None:
    course, skill = _complete_and_confirm(client)
    matched = matching_repository.load_profile("aisyah").skills
    assert matched[skill] == course.level
    learner = pathway_service.learner_for(LEARNER)
    assert learner.skill_levels == matched
    proposed = pathway_service.get_pathway(LEARNER, ROLE, "moderate")
    assert next(g for g in proposed.gaps if g.skill_id == skill).status == "have"
    assert skill not in {s.skill_id for s in proposed.steps}
    compared = pathway_service.compare_roles(LEARNER, [ROLE], "moderate")
    assert compared.options[0].skills_to_close == sum(g.status != "have" for g in proposed.gaps)
    response = client.post("/api/v1/pathway/plans", json={"role_id": ROLE})
    assert response.status_code == 200, response.text
    saved = SavedPlan.model_validate(response.json()).pathway
    assert skill not in {s.skill_id for s in saved.steps}
    members = org_service.member_learners("org-demo-bank")
    assert members["aisyah"].skill_levels == matched
    assert pathway_service.team_gaps({"aisyah": members["aisyah"]}, [ROLE])
    assert (
        next(
            gap
            for role, sid, gap in pathway_service.team_gaps({"aisyah": members["aisyah"]}, [ROLE])
            if sid == skill
        )
        == 0
    )
    team = pathway_service.group_pathway({"aisyah": members["aisyah"]}, ROLE, "moderate", True)
    assert skill not in {s.skill_id for s in team.steps}


def test_rejection_after_target_change_removes_previous_credit(client: TestClient) -> None:
    course, skill = _complete_and_confirm(client)
    other_role = next(role for role in data.target_role_ids() if role != ROLE)
    assert client.post("/api/v1/pathway/plans", json={"role_id": other_role}).status_code == 200
    evidence = repository.evidence("aisyah", ROLE)[course.id]
    response = client.post(
        "/api/v1/pathway/verifications",
        json={
            "user_id": "aisyah",
            "role_id": ROLE,
            "course_id": course.id,
            "decision": "reject",
            "submitted_at": evidence.submitted_at.isoformat(),
        },
        headers={"X-Demo-User": "demo-company"},
    )
    assert response.status_code == 200, response.text
    assert skill not in pathway_service.evidenced_levels("aisyah")


def test_undo_after_target_change_removes_credit(client: TestClient) -> None:
    course, skill = _complete_and_confirm(client)
    other_role = next(role for role in data.target_role_ids() if role != ROLE)
    assert client.post("/api/v1/pathway/plans", json={"role_id": other_role}).status_code == 200
    response = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course.id, "status": "not_started"},
    )
    assert response.status_code == 200, response.text
    assert skill not in pathway_service.evidenced_levels("aisyah")


def test_multiple_targets_take_highest_level_without_cross_user_leaks() -> None:
    for role, level in [("r1", 3), ("r2", 4)]:
        course = _course("same-course", ["sql"], level)
        repository.set_course_status("aisyah", role, course.id, "completed", course)
        repository.save_evidence(
            "aisyah", _evidence(course.id, "org_confirmed").model_copy(update={"role_id": role})
        )
    assert pathway_service.evidenced_levels("aisyah") == {"sql": 4}
    assert pathway_service.evidenced_levels("ravi") == {}
    repository.set_course_status("aisyah", "r2", "same-course", "not_started")
    assert pathway_service.evidenced_levels("aisyah") == {"sql": 3}


def test_later_course_edits_do_not_rewrite_recorded_learning() -> None:
    original = _course("c", ["sql"], 3)
    repository.set_course_status("aisyah", ROLE, "c", "in_progress", original)
    changed = original.model_copy(update={"level": 5, "skill_ids": ["python"]})
    repository.set_course_status("aisyah", ROLE, "c", "completed", changed)
    repository.save_evidence(
        "aisyah", _evidence("c", "org_confirmed").model_copy(update={"role_id": ROLE})
    )
    assert pathway_service.evidenced_levels("aisyah") == {"sql": 3}


@pytest.mark.usefixtures("pg_backend")
def test_course_facts_survive_new_postgres_store_and_catalogue_edits(client: TestClient) -> None:
    course, skill = _complete_and_confirm(client)
    fresh = repository.PostgresStore()
    assert fresh.course_facts("aisyah", ROLE)[course.id] == course
    # Attempting to upsert later catalogue facts must not rewrite the original snapshot.
    fresh.set_course_status(
        "aisyah", ROLE, course.id, "completed", course.model_copy(update={"level": 1})
    )
    assert repository.PostgresStore().course_facts("aisyah", ROLE)[course.id] == course
    assert pathway_service.evidenced_levels("aisyah")[skill] == course.level


@pytest.mark.usefixtures("pg_backend")
def test_migration_backfills_saved_and_replaced_target_progress(client: TestClient) -> None:
    from db.migrate import MIGRATIONS, up_section

    course, _skill = _complete_and_confirm(client)
    # An older target with no surviving saved plan must use catalogue facts during upgrade.
    repository.set_course_status("aisyah", "old-target", course.id, "completed")
    migration = MIGRATIONS / "20261022220000_core_completion_course_snapshots.sql"
    with connection() as conn, conn.transaction(force_rollback=True):
        conn.execute("ALTER TABLE course_progress DROP COLUMN course_snapshot")
        conn.execute(up_section(migration.read_text(encoding="utf-8")))
        rows = conn.execute(
            "SELECT role_id, course_snapshot FROM course_progress "
            "WHERE user_id = %s AND course_id = %s",
            ("aisyah", course.id),
        ).fetchall()
        facts = {row["role_id"]: Course.model_validate(row["course_snapshot"]) for row in rows}
        assert facts[ROLE] == course
        assert facts["old-target"].skill_ids == course.skill_ids
        assert facts["old-target"].level == course.level


def test_replan_preserves_completed_history_badges_and_undo(
    client: TestClient, learning_backend: None
) -> None:
    course, skill = _complete_and_confirm(client)
    before = Progress.model_validate(client.get("/api/v1/pathway/progress").json())
    before_badges = {badge.id for badge in before.badges}
    assert "milestone:first" in before_badges
    response = client.post("/api/v1/pathway/plans/me/accept-replan")
    assert response.status_code == 200, response.text
    after = Progress.model_validate(client.get("/api/v1/pathway/progress").json())
    assert course.id not in {c.id for s in after.pathway.steps for c in s.courses}
    assert any(item.role_id == ROLE and item.course == course for item in after.history)
    assert before_badges <= {badge.id for badge in after.badges}
    assert after.percent_complete > 0
    assert repository.plan_history("aisyah")
    if isinstance(repository.store(), repository.PostgresStore):
        assert repository.PostgresStore().plan_history("aisyah")
    response = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course.id, "status": "not_started"},
    )
    assert response.status_code == 200, response.text
    undone = Progress.model_validate(response.json())
    assert course.id not in {item.course.id for item in undone.history}
    assert "milestone:first" not in {badge.id for badge in undone.badges}
    assert skill not in pathway_service.evidenced_levels("aisyah")


def test_new_target_keeps_old_history_and_badges(client: TestClient) -> None:
    course, _skill = _complete_and_confirm(client)
    other = next(role for role in data.target_role_ids() if role != ROLE)
    assert client.post("/api/v1/pathway/plans", json={"role_id": other}).status_code == 200
    body = Progress.model_validate(client.get("/api/v1/pathway/progress").json())
    assert body.role_id == other
    assert any(item.role_id == ROLE and item.course == course for item in body.history)
    assert "milestone:first" in {badge.id for badge in body.badges}
    assert (
        pathway_service.get_progress(
            CurrentUser("ravi", "Ravi", "learner"), other, "moderate"
        ).history
        == []
    )


def test_rejection_after_replan_removes_badges_but_keeps_reviewable_history(
    client: TestClient,
) -> None:
    course, _skill = _complete_and_confirm(client)
    assert client.post("/api/v1/pathway/plans/me/accept-replan").status_code == 200
    evidence = repository.evidence("aisyah", ROLE)[course.id]
    response = client.post(
        "/api/v1/pathway/verifications",
        json={
            "user_id": "aisyah",
            "role_id": ROLE,
            "course_id": course.id,
            "decision": "reject",
            "submitted_at": evidence.submitted_at.isoformat(),
        },
        headers={"X-Demo-User": "demo-company"},
    )
    assert response.status_code == 200, response.text
    body = Progress.model_validate(client.get("/api/v1/pathway/progress").json())
    assert "milestone:first" not in {badge.id for badge in body.badges}
    assert body.history[0].evidence.kind == "org_rejected"


def test_team_earned_learning_is_one_batch_read_and_members_are_loaded_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    loads: list[str] = []
    read_learning = repository.learning_records
    load_members = org_service.repository.list_members

    def learning(user_ids: list[str]) -> list[repository.LearningRecord]:
        calls.append(user_ids)
        return read_learning(user_ids)

    def members(org_id: str) -> list[Member]:
        loads.append(org_id)
        return load_members(org_id)

    monkeypatch.setattr(repository, "learning_records", learning)
    monkeypatch.setattr(org_service.repository, "list_members", members)
    manager = CurrentUser("demo-company", "Demo HR", "org_admin", "org-demo-bank")
    org_service.get_plan(manager, "moderate")
    assert loads == ["org-demo-bank"]
    assert len(calls) == 1 and "aisyah" in calls[0]
    calls.clear()
    loads.clear()
    org_service.member_plans("org-demo-bank", "moderate")
    assert loads == ["org-demo-bank"]
    assert len(calls) == 1


def test_postgres_learning_read_joins_all_targets_in_one_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []
    store = repository.PostgresStore()
    course = _course("learned", ["sql"], 3)
    evidence = _evidence("learned", "org_confirmed")
    user_ids = [f"synthetic-{i}" for i in range(100)]

    def query(sql: str, params: tuple[object, ...]) -> list[tuple[object, ...]]:
        calls.append((sql, params))
        return [
            (uid, f"target-{target}", course.id, "completed",
             course.model_dump(mode="json"), evidence.model_dump(mode="json"))
            for uid in user_ids for target in range(3)
        ]  # fmt: skip

    monkeypatch.setattr(store, "_run", query)
    monkeypatch.setattr(repository, "learning_records", store.learning_records)
    levels = pathway_service.evidenced_levels_many(user_ids)
    assert levels == {uid: {"sql": 3} for uid in user_ids}
    assert len(calls) == 1
    assert calls[0][1] == (user_ids,)
    assert "LEFT JOIN course_evidence" in calls[0][0]
    calls.clear()
    assert store.learning_records([]) == [] and calls == []
