"""Synthetic expense workflow: scope, budget races, evidence and payment are separate gates."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from harness import fixtures

from app.contracts.funding import FundingDecision, MemberBudgetIn
from app.contracts.pathway import CompletionEvidence
from app.core.auth import CurrentUser
from app.core.errors import AppError
from app.features.org import funding, funding_store
from app.features.pathway import repository, verification

HR = {"X-Demo-User": "demo-company"}
MEMBER = {"X-Demo-User": "aisyah"}
OTHER = {"X-Demo-User": "weijie"}
MANAGER = CurrentUser("demo-company", "Synthetic HR", "org_admin", "org-demo-bank")
YEAR = datetime.now(UTC).year
ROOT = f"/api/v1/org/funding/{YEAR}"


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures.install()
    funding_store._memory.clear()
    repository.reset()
    monkeypatch.setattr(verification, "probe", lambda _url: 200)


def _request(
    client: TestClient, course: str = "aitraining2u-ai-data-analytics", amount: str = "500.00"
) -> dict:
    response = client.post(
        ROOT + "/requests",
        headers=MEMBER,
        json={
            "course_id": course,
            "role_id": "data-analyst",
            "amount_myr": amount,
            "quote_url": "https://example.com/synthetic-quote",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["claims"][-1]


def _decision(client: TestClient, claim: dict, action: str, **extra: str):
    return client.post(
        ROOT + f"/requests/{claim['id']}/decision",
        headers=HR,
        json={"revision": claim["revision"], "action": action, **extra},
    )


def _approved(client: TestClient) -> dict:
    response = client.put(
        ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": "800.00"}
    )
    assert response.status_code == 200
    claim = _request(client)
    response = _decision(client, claim, "approve")
    assert response.status_code == 200, response.text
    return response.json()["claims"][0]


def _proof(claim: dict) -> None:
    course = next(c for c in funding.ledger(MANAGER, YEAR).claims if c.id == claim["id"]).course
    repository.set_course_status("aisyah", claim["role_id"], course.id, "completed", course)
    repository.save_evidence(
        "aisyah",
        CompletionEvidence(
            role_id=claim["role_id"],
            course_id=course.id,
            kind="org_confirmed",
            url="https://example.com/synthetic-certificate",
            submitted_at=datetime.now(UTC),
            reviewed_by="demo-company",
            reviewed_at=datetime.now(UTC),
        ),
    )


def _submit(
    client: TestClient, claim: dict, amount: str = "450.00", purchased_at: str | None = None
):
    return client.post(
        ROOT + f"/requests/{claim['id']}/submit",
        headers=MEMBER,
        json={
            "revision": claim["revision"],
            "amount_myr": amount,
            "receipt_url": "https://example.com/synthetic-receipt",
            "receipt_reference": "DEMO-001",
            "purchased_at": purchased_at or datetime.now(UTC).isoformat(),
        },
    )


def test_claim_has_separate_budget_completion_receipt_and_external_payment_gates(
    client: TestClient,
):
    claim = _approved(client)
    balance = client.get(ROOT, headers=MEMBER).json()["budgets"][0]
    assert Decimal(balance["reserved_myr"]) == 500 and Decimal(balance["available_myr"]) == 300
    assert _submit(client, claim).status_code == 409  # ticking completed is insufficient
    _proof(claim)
    assert _submit(client, claim, "501.00").status_code == 409
    before_approval = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert _submit(client, claim, purchased_at=before_approval).status_code == 409
    response = _submit(client, claim)
    assert response.status_code == 200, response.text
    submitted = response.json()["claims"][0]
    assert submitted["status"] == "submitted"
    assert (
        _decision(client, submitted, "mark_paid", payment_reference="DEMO-PAY").status_code == 409
    )
    accepted = _decision(client, submitted, "accept_claim").json()["claims"][0]
    assert _decision(client, accepted, "mark_paid").status_code == 409
    response = _decision(client, accepted, "mark_paid", payment_reference="DEMO-PAY-001")
    assert response.status_code == 200
    assert response.json()["claims"][0]["status"] == "paid"
    balance = response.json()["budgets"][0]
    assert Decimal(balance["paid_myr"]) == 450 and Decimal(balance["reserved_myr"]) == 0
    assert Decimal(balance["available_myr"]) == 350
    assert (
        _decision(client, accepted, "mark_paid", payment_reference="DEMO-PAY-001").status_code
        == 409
    )


def test_evidence_revocation_blocks_payment(client: TestClient):
    claim = _approved(client)
    _proof(claim)
    submitted = _submit(client, claim).json()["claims"][0]
    accepted = _decision(client, submitted, "accept_claim").json()["claims"][0]
    ev = repository.evidence("aisyah", claim["role_id"])[claim["course"]["id"]]
    repository.save_evidence("aisyah", ev.model_copy(update={"kind": "org_rejected"}))
    assert _decision(client, accepted, "mark_paid", payment_reference="DEMO-PAY").status_code == 409


def test_approved_course_outside_algorithmic_plan_can_submit_a_certificate(client: TestClient):
    claim = _approved(client)
    response = client.post(
        ROOT + f"/requests/{claim['id']}/completion",
        headers=MEMBER,
        json={"revision": claim["revision"], "url": "https://example.com/synthetic-certificate"},
    )
    assert response.status_code == 200, response.text
    assert repository.course_status("aisyah", "data-analyst")[claim["course"]["id"]] == "completed"
    assert client.get("/api/v1/pathway/verifications", headers=HR).json()["pending"] == 1
    assert _submit(client, response.json()["claims"][0]).status_code == 409


def test_scope_ownership_duplicates_and_stale_reviews(client: TestClient):
    claim = _approved(client)
    assert client.get(ROOT, headers=OTHER).status_code == 404
    assert client.get(ROOT, headers=MEMBER).json()["budgets"][0]["user_id"] == "aisyah"
    assert (
        client.put(
            ROOT + "/budget", headers=MEMBER, json={"user_id": "aisyah", "amount_myr": 1000}
        ).status_code
        == 403
    )
    assert (
        client.post(
            ROOT + f"/requests/{claim['id']}/decision",
            headers=OTHER,
            json={"revision": claim["revision"], "action": "approve"},
        ).status_code
        == 404
    )
    assert _decision(client, {**claim, "revision": 1}, "reject", note="Test").status_code == 409
    assert (
        client.put(
            ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": 100}
        ).status_code
        == 409
    )
    duplicate = client.post(
        ROOT + "/requests",
        headers=MEMBER,
        json={
            "course_id": claim["course"]["id"],
            "role_id": "data-analyst",
            "amount_myr": 500,
            "quote_url": "https://example.com/synthetic-quote",
        },
    )
    assert duplicate.status_code == 409


def test_concurrent_approvals_cannot_overspend_member_budget(client: TestClient):
    funding.budget(MANAGER, YEAR, MemberBudgetIn(user_id="aisyah", amount_myr=Decimal(600)))
    claims = [_request(client), _request(client, "ukm-data-analytics-certificate")]

    def approve(claim: dict) -> bool:
        try:
            funding.decide(
                MANAGER, YEAR, claim["id"], FundingDecision(revision=1, action="approve")
            )
            return True
        except AppError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(approve, claims)) == 1
    assert funding.ledger(MANAGER, YEAR).budgets[0].reserved_myr <= 600


def test_export_and_deletion_include_embedded_funding_records(client: TestClient):
    claim = _approved(client)
    exported = client.get("/api/v1/auth/me/export", headers=MEMBER).json()
    assert exported["learning_funding"][0]["claims"][0]["id"] == claim["id"]
    assert "emp-002" not in str(exported["learning_funding"])
    funding_store.forget_user("aisyah")
    assert funding_store.export_user("aisyah") == []


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", "0.001"])
def test_invalid_money_is_rejected(client: TestClient, amount: str):
    response = client.put(
        ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": amount}
    )
    assert response.status_code == 422
