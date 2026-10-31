"""Employer proposals remain member-controlled, scoped and catalogue-grounded."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import BANK, work_headers

from app.core import accounts
from app.features.org import funding_store
from app.features.pathway import repository

HR = {"X-Demo-User": "demo-company", "X-Workspace": BANK}
WORK = work_headers()
# Keep planning above the default privacy cohort gate.
pytestmark = pytest.mark.usefixtures("planning_cohort")
# Aisyah plus the two synthetic sharing members added by planning_cohort.
COHORT = ["aisyah", "synthetic-cohort-third", "synthetic-cohort-fourth"]


@pytest.fixture(autouse=True)
def fresh_plans() -> None:
    repository.reset()


def send(client: TestClient) -> str:
    brief = {
        "title": "Synthetic GBS learning team",
        "objectives": ["data_driven"],
        "roles": [{"role_id": "data-analyst", "headcount": 1}],
        "member_ids": COHORT,
        "target_date": (date.today() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 1000,
        "budget_per_member_myr": 1000,
    }
    plan = client.post("/api/v1/org/programmes/generate", headers=HR, json=brief)
    assert plan.status_code == 200, plan.text
    sent = client.post(
        "/api/v1/org/programmes",
        headers=HR,
        json={"brief": brief, "token": plan.json()["token"]},
    )
    assert sent.status_code == 201, sent.text
    return sent.json()["record"]["id"]


def test_proposal_does_not_change_target_or_imply_acceptance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        accounts._memory,
        "emp-002",
        (
            accounts.Account("emp-002", "Synthetic coworker", None, "learner", BANK),
            None,
        ),
    )
    pid = send(client)
    endpoint = f"/api/v1/org/programmes/{pid}/decision"
    assert client.get("/api/v1/pathway/progress", headers=WORK).status_code == 404
    request = {
        "decision": "request_change",
        "reason": "target_role",
        "proposed_role_id": "business-analyst",
    }
    response = client.post(endpoint, headers=WORK, json=request)
    assert response.status_code == 200, response.text
    assignment = response.json()
    assert assignment["status"] == "change_requested"
    assert assignment["agreement"]["role_id"] == "data-analyst"
    assert assignment["proposed_role_id"] == "business-analyst"
    assert assignment["proposed_role_label"]
    assert assignment["pathway"]["meta"]["sources"]
    assert repository.get_plan("aisyah") is None
    assert client.get("/api/v1/pathway/progress", headers=WORK).status_code == 404
    visible = client.get("/api/v1/org/programmes", headers=HR).json()["programmes"][0]
    assert visible["assignments"][0]["proposed_role_id"] == "business-analyst"
    # Only the assigned member can answer; an unrelated workspace is refused before mutation.
    assert client.post(endpoint, headers=work_headers("emp-002"), json=request).status_code == 404
    assert client.post(endpoint, headers=work_headers("ravi"), json=request).status_code == 403
    assert (
        client.post(
            endpoint, headers=work_headers(org_id="org-demo-poly"), json=request
        ).status_code
        == 403
    )
    for invalid in ["made-up-target", "data-analyst"]:
        assert (
            client.post(
                endpoint, headers=WORK, json={**request, "proposed_role_id": invalid}
            ).status_code
            == 422
        )
    accepted = client.post(endpoint, headers=WORK, json={"decision": "accept"})
    assert accepted.status_code == 200
    assert accepted.json()["proposed_role_id"] is None
    assert client.get("/api/v1/pathway/progress", headers=WORK).status_code == 200


def test_quick_package_proposal_is_visible_to_hr_and_can_be_accepted(client: TestClient) -> None:
    offer = client.get(
        "/api/v1/org/packages",
        headers=HR,
        params={"role_id": "data-analyst", "member_ids": COHORT},
    ).json()["packages"][0]
    selected = client.post(
        "/api/v1/org/packages/select",
        headers=HR,
        json={
            "role_id": "data-analyst",
            "member_ids": COHORT,
            "kind": offer["kind"],
            "token": offer["token"],
            "scenario": "moderate",
        },
    )
    assert selected.status_code == 200
    endpoint = "/api/v1/org/packages/assigned/propose-role"
    request = {"token": offer["token"], "proposed_role_id": "business-analyst"}
    assert (
        client.post(
            endpoint, headers=WORK, json={**request, "proposed_role_id": "made-up"}
        ).status_code
        == 422
    )
    assert (
        client.post(endpoint, headers=WORK, json={**request, "token": "0" * 64}).status_code == 409
    )
    response = client.post(endpoint, headers=WORK, json=request)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "change_requested"
    assert response.json()["agreement"]["role_id"] == "data-analyst"
    assert response.json()["pathway"]["meta"]["sources"]
    reviewed = client.get("/api/v1/org/programmes", headers=HR).json()["package_assignments"]
    assert reviewed[0]["proposed_role_id"] == "business-analyst"
    pid = response.json()["agreement"]["programme_id"]
    accepted = client.post(
        f"/api/v1/org/programmes/{pid}/decision", headers=WORK, json={"decision": "accept"}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert repository.get_plan("aisyah") is None
    assert funding_store.snapshot(BANK).assignments
