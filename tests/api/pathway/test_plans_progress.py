from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.contracts.pathway import Progress, ReplanStatus, SavedPlan
from app.features.pathway import data

ROLE = "process-automation-analyst"


def _save(client: TestClient, role: str = ROLE) -> SavedPlan:
    resp = client.post("/api/v1/pathway/plans", json={"role_id": role, "scenario": "moderate"})
    assert resp.status_code == 200, resp.text
    return SavedPlan.model_validate(resp.json())


def _progress(client: TestClient, course_id: str, status: str = "completed") -> Progress:
    resp = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": course_id, "status": status},
    )
    assert resp.status_code == 200, resp.text
    return Progress.model_validate(resp.json())


def test_no_saved_plan_yet(client: TestClient) -> None:
    body = ReplanStatus.model_validate(client.get("/api/v1/pathway/plans/me").json())
    assert body.saved is None and not body.needs_replan


def test_saved_plan_on_latest_snapshot_needs_no_replan(client: TestClient) -> None:
    saved = _save(client)
    body = ReplanStatus.model_validate(client.get("/api/v1/pathway/plans/me").json())
    assert body.saved and body.saved.role_id == ROLE
    assert body.latest_snapshot_version == saved.snapshot_version
    assert not body.needs_replan and body.proposed is None


def test_new_trend_snapshot_proposes_a_replan(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = _save(client)
    old_first = saved.pathway.steps[0].skill_id
    newer = data.Snapshot(
        "99", "synthetic-1", Source(name="SYNTHETIC TEST", url="", retrieved_at=date(2026, 11, 1))
    )
    monkeypatch.setattr(data, "latest_snapshot", lambda: newer)
    # Python demand jumps in the new snapshot, so it should move up the plan.
    monkeypatch.setattr(data, "skill_growth", lambda _id: {"python": 1.0, "rpa": -0.5})
    body = ReplanStatus.model_validate(client.get("/api/v1/pathway/plans/me").json())
    assert body.needs_replan and body.changes and body.proposed
    assert body.proposed.steps[0].skill_id == "python" != old_first
    assert "SYNTHETIC TEST" in body.message
    accepted = SavedPlan.model_validate(
        client.post("/api/v1/pathway/plans/me/accept-replan").json()
    )
    assert accepted.snapshot_version == "synthetic-1"


def test_progress_raises_levels_and_awards_badges(client: TestClient) -> None:
    plan = _save(client).pathway
    rpa_step = next(s for s in plan.steps if s.skill_id == "rpa")
    first = _progress(client, rpa_step.courses[0].id)
    assert "milestone:first" in {b.id for b in first.badges}
    assert all(b.evidence == "self_reported" for b in first.badges)
    for c in rpa_step.courses:
        body = _progress(client, c.id)
    rpa = next(s for s in body.skills if s.skill_id == "rpa")
    assert rpa.closed and rpa.current_level >= rpa.target_level
    assert "skill:rpa" in {b.id for b in body.badges}
    assert 0 < body.percent_complete < 1
    for step in plan.steps:
        for c in step.courses:
            body = _progress(client, c.id)
    assert body.percent_complete == 1 and body.gap_closed == body.gap_total
    assert {"milestone:halfway", "milestone:complete"} <= {b.id for b in body.badges}


def test_progress_can_be_undone(client: TestClient) -> None:
    course_id = _save(client).pathway.steps[0].courses[0].id
    assert {b.id for b in _progress(client, course_id).badges} >= {"milestone:first"}
    undone = _progress(client, course_id, "not_started")
    assert undone.course_status == {}
    assert undone.badges == [], "badges follow current progress"


def test_progress_rejects_courses_outside_the_plan(client: TestClient) -> None:
    _save(client)
    resp = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": "made-up-course", "status": "completed"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unknown_course"


def test_progress_tracks_and_returns_the_saved_plan(client: TestClient) -> None:
    saved = _save(client)
    body = Progress.model_validate(
        client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    )
    assert body.pathway == saved.pathway


def test_profile_change_is_proposed_not_applied(client: TestClient) -> None:
    from app.features.profile import repository as profiles

    original = profiles.get_profile("aisyah")
    assert original is not None
    saved = _save(client)
    try:
        skills = [s.model_dump() for s in original.skills]
        skills.append({"skill_id": "rpa", "level": 3, "source": "confirmed"})
        client.put("/api/v1/profile/skills", json={"skills": skills})
        status = ReplanStatus.model_validate(client.get("/api/v1/pathway/plans/me").json())
        assert status.needs_replan and "profile changed" in status.message
        assert status.saved and status.saved.pathway == saved.pathway  # nothing applied yet
        assert status.proposed and "rpa" not in [s.skill_id for s in status.proposed.steps]
        # Progress still follows the saved plan until the learner accepts.
        progress = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
        assert "rpa" in [s["skill_id"] for s in progress["pathway"]["steps"]]
    finally:
        profiles.save_profile(original)


def test_other_scenario_uses_a_fresh_plan(client: TestClient) -> None:
    _save(client)  # moderate
    body = client.get("/api/v1/pathway/progress", params={"role_id": ROLE, "scenario": "fast"})
    assert Progress.model_validate(body.json()).pathway.meta.scenario == "fast"
