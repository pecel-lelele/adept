"""Employer programmes: objective-first briefs, personalised routes, budgets, agreements."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.features.org import funding_store
from app.features.pathway import repository

HR = {"X-Demo-User": "demo-company"}
MEMBER = {"X-Demo-User": "aisyah"}


@pytest.fixture(autouse=True)
def _fresh_store() -> None:
    funding_store._memory.clear()


def _brief(client: TestClient, **over: object) -> dict:
    opts = client.get("/api/v1/org/programmes/options", headers=HR)
    assert opts.status_code == 200, opts.text
    members = [m["user_id"] for m in opts.json()["members"]]
    brief = {
        "title": "AI in operations reporting",
        "objectives": ["ai_adoption", "data_driven"],
        "roles": [
            {"role_id": "data-analyst", "headcount": 1},
            {"role_id": "business-analyst", "headcount": 5},
        ],
        "member_ids": members,
        "target_date": (datetime.now(UTC).date() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 3000,
        "budget_per_member_myr": 2000,
    }
    brief.update(over)
    return brief


def _generate(client: TestClient, brief: dict) -> dict:
    resp = client.post("/api/v1/org/programmes/generate", headers=HR, json=brief)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_options_are_for_managers_and_map_objectives_to_catalogue_roles(client: TestClient) -> None:
    assert client.get("/api/v1/org/programmes/options", headers=MEMBER).status_code == 403
    body = client.get("/api/v1/org/programmes/options", headers=HR).json()
    assert body["meta"]["sources"] and body["meta"]["snapshot_date"]
    assert body["meta"]["scenario"] == "moderate" and body["meta"]["is_estimate"]
    roles = {r["role_id"] for r in body["roles"]}
    for objective in body["objectives"]:
        assert set(objective["role_ids"]) <= roles, objective["id"]
    assert body["members"], "the demo organisation has members with completed profiles"


def test_people_are_matched_within_headcount_and_routes_are_personal(client: TestClient) -> None:
    plan = _generate(client, _brief(client))
    analysts = [r for r in plan["routes"] if r["role_id"] == "data-analyst"]
    assert len(analysts) <= 1
    for route in plan["routes"]:
        assert route["route"] in {"foundation", "applied", "advanced"}
        assert 0 <= route["readiness"] <= 1
        assert route["weeks_available"] >= 11
        assert route["on_track"] == (route["weeks_needed"] <= route["weeks_available"])
    assert plan["notes"] and len(plan["token"]) == 64


def test_programme_ceiling_and_individual_limit_are_both_respected(client: TestClient) -> None:
    plan = _generate(client, _brief(client, budget_total_myr=500, budget_per_member_myr=400))
    assert plan["total_cost_myr"] <= 500
    assert all(r["cost_myr"] <= r["budget_myr"] <= 400 for r in plan["routes"])
    assert plan["within_programme_budget"]


def test_restrictions_filter_the_courses_used(client: TestClient) -> None:
    plan = _generate(client, _brief(client, certificate_required=True, hrd_claimable_only=True))
    for route in plan["routes"]:
        for step in route["pathway"]["steps"]:
            for course in step["courses"]:
                assert course["price_status"] == "listed"
                assert course["hrd_claimable"] or course["cost_myr"] == 0


def test_a_past_target_date_is_refused(client: TestClient) -> None:
    brief = _brief(client, target_date=datetime.now(UTC).date().isoformat())
    resp = client.post("/api/v1/org/programmes/generate", headers=HR, json=brief)
    assert resp.status_code == 422


def test_send_refuses_a_changed_plan(client: TestClient) -> None:
    brief = _brief(client)
    plan = _generate(client, brief)
    stale = client.post(
        "/api/v1/org/programmes", headers=HR, json={"brief": brief, "token": "0" * 64}
    )
    assert stale.status_code == 409
    sent = client.post(
        "/api/v1/org/programmes", headers=HR, json={"brief": brief, "token": plan["token"]}
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["pending"] == len(plan["routes"])


def test_member_agreement_accept_keeps_the_personal_plan_and_tracks_work_progress(
    client: TestClient,
) -> None:
    brief = _brief(client, mandatory=True)
    plan = _generate(client, brief)
    client.post("/api/v1/org/programmes", headers=HR, json={"brief": brief, "token": plan["token"]})
    mine = client.get("/api/v1/org/programmes/mine", headers=MEMBER).json()["assignments"]
    if not mine:
        pytest.skip("aisyah was not assigned in this brief")
    agreement = mine[0]["agreement"]
    pid = agreement["programme_id"]
    assert agreement["mandatory"] and agreement["hours_per_week"] == 4

    declined = client.post(
        f"/api/v1/org/programmes/{pid}/decision", headers=MEMBER, json={"decision": "decline"}
    )
    assert declined.status_code == 409, "required programmes cannot be declined"
    no_reason = client.post(
        f"/api/v1/org/programmes/{pid}/decision",
        headers=MEMBER,
        json={"decision": "request_change"},
    )
    assert no_reason.status_code == 422

    personal_before = repository.get_plan("aisyah")
    accepted = client.post(
        f"/api/v1/org/programmes/{pid}/decision", headers=MEMBER, json={"decision": "accept"}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert repository.get_plan("aisyah") == personal_before

    role = agreement["role_id"]
    work = client.get(
        "/api/v1/pathway/progress", headers=MEMBER, params={"role_id": role, "plan": "work"}
    )
    assert work.status_code == 200, work.text
    courses = [c for s in accepted.json()["pathway"]["steps"] for c in s["courses"]]
    if courses:
        done = client.post(
            "/api/v1/pathway/progress",
            headers=MEMBER,
            params={"plan": "work"},
            json={"role_id": role, "course_id": courses[0]["id"], "status": "completed"},
        )
        assert done.status_code == 200, done.text

    status = client.get("/api/v1/org/programmes", headers=HR).json()["programmes"][0]
    assert status["accepted"] == 1


def test_members_cannot_generate_or_send(client: TestClient) -> None:
    brief = _brief(client)
    assert (
        client.post("/api/v1/org/programmes/generate", headers=MEMBER, json=brief).status_code
        == 403
    )
    assert client.get("/api/v1/org/programmes", headers=MEMBER).status_code == 403


def test_non_sharing_member_acceptance_requires_consent_and_sanitizes_for_hr(
    client: TestClient,
) -> None:
    brief = _brief(client)
    plan = _generate(client, brief)
    client.post("/api/v1/org/programmes", headers=HR, json={"brief": brief, "token": plan["token"]})
    mine = client.get("/api/v1/org/programmes/mine", headers=MEMBER).json()["assignments"]
    if not mine:
        pytest.skip("aisyah was not assigned in this brief")
    pid = mine[0]["agreement"]["programme_id"]

    member_org = {**MEMBER, "X-Workspace": "org-demo-bank"}

    try:
        # Member switches off skills sharing
        resp = client.put(
            "/api/v1/org/me/sharing", headers=member_org, json={"share_skills": False}
        )
        assert resp.status_code == 200

        # Accepting without consent is refused
        bad = client.post(
            f"/api/v1/org/programmes/{pid}/decision",
            headers=member_org,
            json={"decision": "accept", "consent": False},
        )
        assert bad.status_code == 400
        assert bad.json()["error"]["code"] == "sharing_consent_required"

        # Accepting with explicit consent succeeds
        good = client.post(
            f"/api/v1/org/programmes/{pid}/decision",
            headers=member_org,
            json={"decision": "accept", "consent": True},
        )
        assert good.status_code == 200

        # HR view of list_programmes masks private skills for members whose sharing is off
        programmes = client.get("/api/v1/org/programmes", headers=HR).json()["programmes"]
        assert programmes
        aisyah_assignment = next(
            a for a in programmes[0]["assignments"] if a["user_id"] == "aisyah"
        )
        route = aisyah_assignment["pathway"]
        # Gap statuses and starting levels come from private levels: none reach HR.
        assert route["gaps"] == []
        assert all(u["current_level"] == 0 for u in route["unmet"])
        assert all(step["current_level"] == 0 for step in route["steps"])
    finally:
        client.put("/api/v1/org/me/sharing", headers=member_org, json={"share_skills": True})
