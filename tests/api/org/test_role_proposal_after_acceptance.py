"""Proposing a different role after accepting must not withdraw the member's acceptance."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import BANK, work_headers

from app.features.pathway import repository

HR = {"X-Demo-User": "demo-company", "X-Workspace": BANK}
WORK = work_headers()
PROPOSAL = {
    "decision": "request_change",
    "reason": "target_role",
    "proposed_role_id": "business-analyst",
}


@pytest.fixture(autouse=True)
def fresh_plans() -> None:
    repository.reset()


def _accepted_programme(client: TestClient) -> str:
    brief = {
        "title": "Synthetic GBS learning team",
        "objectives": ["data_driven"],
        "roles": [{"role_id": "data-analyst", "headcount": 1}],
        "member_ids": ["aisyah"],
        "target_date": (date.today() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 1000,
        "budget_per_member_myr": 1000,
    }
    plan = client.post("/api/v1/org/programmes/generate", headers=HR, json=brief).json()
    sent = client.post(
        "/api/v1/org/programmes", headers=HR, json={"brief": brief, "token": plan["token"]}
    )
    assert sent.status_code == 201, sent.text
    pid = sent.json()["record"]["id"]
    accepted = client.post(
        f"/api/v1/org/programmes/{pid}/decision", headers=WORK, json={"decision": "accept"}
    )
    assert accepted.status_code == 200, accepted.text
    return pid


def test_programme_proposal_keeps_acceptance_and_recorded_progress(client: TestClient) -> None:
    pid = _accepted_programme(client)
    before = client.get("/api/v1/pathway/progress", headers=WORK)
    assert before.status_code == 200
    course = next(s for s in before.json()["pathway"]["steps"] if s["courses"])["courses"][0]
    done = client.post(
        "/api/v1/pathway/progress",
        headers=WORK,
        json={"role_id": "data-analyst", "course_id": course["id"], "status": "completed"},
    )
    assert done.status_code == 200, done.text

    response = client.post(f"/api/v1/org/programmes/{pid}/decision", headers=WORK, json=PROPOSAL)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert body["agreement"]["role_id"] == "data-analyst"
    assert body["proposed_role_id"] == "business-analyst"
    assert body["proposed_role_label"]
    after = client.get("/api/v1/pathway/progress", headers=WORK)
    assert after.status_code == 200
    assert after.json()["course_status"][course["id"]] == "completed"
    status = client.get("/api/v1/org/programmes", headers=HR).json()["programmes"][0]
    assert status["accepted"] == 1 and status["change_requested"] == 0
    assert status["assignments"][0]["proposed_role_id"] == "business-analyst"


def test_quick_package_proposal_keeps_an_existing_acceptance(client: TestClient) -> None:
    offer = client.get(
        "/api/v1/org/packages",
        headers=HR,
        params={"role_id": "data-analyst", "member_ids": ["aisyah"]},
    ).json()["packages"][0]
    assert (
        client.post(
            "/api/v1/org/packages/select",
            headers=HR,
            json={
                "role_id": "data-analyst",
                "member_ids": ["aisyah"],
                "kind": offer["kind"],
                "token": offer["token"],
                "scenario": "moderate",
            },
        ).status_code
        == 200
    )
    token = offer["token"]
    assert (
        client.post(
            "/api/v1/org/packages/assigned/accept", headers=WORK, json={"token": token}
        ).status_code
        == 200
    )

    response = client.post(
        "/api/v1/org/packages/assigned/propose-role",
        headers=WORK,
        json={"token": token, "proposed_role_id": "business-analyst"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert response.json()["proposed_role_id"] == "business-analyst"
    assert client.get("/api/v1/pathway/progress", headers=WORK).status_code == 200
