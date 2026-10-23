"""Training budgets: HR sets a yearly amount per member to plan packages; members never claim."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from harness import fixtures

from app.core.auth import CurrentUser
from app.features.org import funding, funding_store

HR = {"X-Demo-User": "demo-company"}
MEMBER = {"X-Demo-User": "aisyah"}
MANAGER = CurrentUser("demo-company", "Synthetic HR", "org_admin", "org-demo-bank")
YEAR = funding.current_year()
ROOT = f"/api/v1/org/funding/{YEAR}"


@pytest.fixture(autouse=True)
def fresh() -> None:
    fixtures.install()
    funding_store._memory.clear()


def test_hr_sets_a_member_budget_and_reads_it_back(client: TestClient):
    response = client.put(
        ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": "800.00"}
    )
    assert response.status_code == 200, response.text
    budget = next(b for b in response.json()["budgets"] if b["user_id"] == "aisyah")
    assert Decimal(budget["amount_myr"]) == Decimal("800.00")
    assert Decimal(budget["available_myr"]) == Decimal("800.00")
    assert funding.ledger(MANAGER, YEAR).claims == []


def test_members_cannot_set_budgets(client: TestClient):
    response = client.put(
        ROOT + "/budget", headers=MEMBER, json={"user_id": "aisyah", "amount_myr": "1"}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    ["/requests", "/requests/x/submit", "/requests/x/completion", "/requests/x/decision"],
)
def test_member_reimbursement_routes_are_gone(client: TestClient, path: str):
    assert client.post(ROOT + path, headers=MEMBER, json={}).status_code in (404, 405)


def test_budget_caps_the_budget_capped_package(client: TestClient):
    client.put(ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": "150.00"})
    response = client.get("/api/v1/org/packages", headers=HR, params={"role_id": "data-analyst"})
    assert response.status_code == 200, response.text
    capped = next(p for p in response.json()["packages"] if p["kind"] == "budget_capped")
    member = next(m for m in capped["members"] if m["user_id"] == "aisyah")
    assert Decimal(str(member["available_budget_myr"])) == Decimal("150")
    assert Decimal(str(member["pathway"]["out_of_pocket_myr"])) <= Decimal("150")


def test_budget_year_switches_at_malaysia_midnight(monkeypatch: pytest.MonkeyPatch):
    class Boundary(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 12, 31, 16, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(funding, "datetime", Boundary)
    assert funding.current_year() == 2027


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", "0.001"])
def test_invalid_money_is_rejected(client: TestClient, amount: str):
    response = client.put(
        ROOT + "/budget", headers=HR, json={"user_id": "aisyah", "amount_myr": amount}
    )
    assert response.status_code == 422
