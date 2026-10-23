import pytest
from fastapi.testclient import TestClient
from harness import fixtures

from app.features.org import funding, funding_store
from app.features.pathway import repository

HR = {"X-Demo-User": "demo-company"}
MEMBER = {"X-Demo-User": "aisyah"}


@pytest.fixture(autouse=True)
def fresh():
    fixtures.install()
    funding_store._memory.clear()
    repository.reset()


def test_hr_compares_proposals_and_member_explicitly_adopts(client: TestClient):
    funding_store._memory.clear()
    repository.reset()
    response = client.get(
        "/api/v1/org/packages",
        headers=HR,
        params={"role_id": "data-analyst", "member_ids": ["aisyah"]},
    )
    assert response.status_code == 200, response.text
    offers = response.json()["packages"]
    assert [p["kind"] for p in offers] == ["free_first", "budget_capped", "broader"]
    assert offers[0]["total_cost_myr"] == 0
    assert offers[2]["total_cost_myr"] >= offers[0]["total_cost_myr"]
    assert offers[2]["unmet_skills"] <= offers[0]["unmet_skills"]
    assert all(p["unmet_skills"] >= 0 and p["meta"]["is_estimate"] for p in offers)
    assert repository.get_plan("aisyah") is None
    offer = offers[0]
    body = {
        "kind": offer["kind"],
        "token": offer["token"],
        "role_id": offer["role_id"],
        "member_ids": ["aisyah"],
        "scenario": "moderate",
    }
    assert client.post("/api/v1/org/packages/select", headers=MEMBER, json=body).status_code == 403
    assert client.post("/api/v1/org/packages/select", headers=HR, json=body).status_code == 200
    assert repository.get_plan("aisyah") is None
    assigned = client.get("/api/v1/org/packages/assigned", headers=MEMBER).json()
    assert assigned["token"] == offer["token"] and "members" not in assigned
    accepted = client.post(
        "/api/v1/org/packages/assigned/accept", headers=MEMBER, json={"token": offer["token"]}
    )
    assert accepted.status_code == 200, accepted.text
    work = accepted.json()
    assert work["status"] == "accepted"
    assert work["agreement"]["role_id"] == "data-analyst"
    # Accepting a team plan never replaces the learner's personal plan.
    assert repository.get_plan("aisyah") is None
    mine = client.get("/api/v1/org/programmes/mine", headers=MEMBER).json()
    assert [a["agreement"]["programme_id"] for a in mine["assignments"]] == [
        work["agreement"]["programme_id"]
    ]


def test_cohort_scope_and_stale_budget_reject_changed_offer(client: TestClient):
    funding_store._memory.clear()
    bad = client.get("/api/v1/org/packages", headers=HR, params={"member_ids": ["weijie"]})
    assert bad.status_code == 400
    assert client.get("/api/v1/org/packages", headers=MEMBER).status_code == 403
    offer = client.get(
        "/api/v1/org/packages",
        headers=HR,
        params={"role_id": "data-analyst", "member_ids": ["aisyah"]},
    ).json()["packages"][1]
    client.put(
        f"/api/v1/org/funding/{funding.current_year()}/budget",
        headers=HR,
        json={"user_id": "aisyah", "amount_myr": "5000.00"},
    )
    response = client.post(
        "/api/v1/org/packages/select",
        headers=HR,
        json={
            "role_id": "data-analyst",
            "member_ids": ["aisyah"],
            "kind": offer["kind"],
            "token": offer["token"],
            "scenario": "moderate",
        },
    )
    assert response.status_code == 409
