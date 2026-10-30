"""Leaving one employer clears its private ledger records without erasing audit history."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from harness import fixtures

from app.contracts.funding import FundingEvent, FundingState
from app.features.org import funding_store, repository


def test_removal_anonymises_events_and_preserves_other_workspaces(client: TestClient) -> None:
    org = "org-demo-bank"
    now = datetime.now(UTC)
    state = FundingState(
        budgets={"2026:aisyah": Decimal(100), "2026:wei-jie": Decimal(200)},
        budget_events=[
            FundingEvent(
                at=now, actor_id="demo-company", action="set_budget", note="aisyah: MYR 100"
            ),
            FundingEvent(at=now, actor_id="aisyah", action="historical", note="private note"),
            FundingEvent(
                at=now, actor_id="demo-company", action="set_budget", note="wei-jie: MYR 200"
            ),
        ],
    )
    funding_store._memory[org] = state
    funding_store._memory["other-employer"] = state.model_copy(deep=True)
    try:
        assert repository.remove_member(org, "aisyah")
        result = funding_store.snapshot(org)
        assert "2026:aisyah" not in result.budgets
        assert result.budgets["2026:wei-jie"] == 200
        assert len(result.budget_events) == 3
        assert result.budget_events[0].note == ""
        assert result.budget_events[1].actor_id == "deleted-account"
        assert result.budget_events[2].note == "wei-jie: MYR 200"
        assert funding_store.snapshot("other-employer").budgets["2026:aisyah"] == 100
        assert all(m.id != "aisyah" for m in repository.list_members(org))
    finally:
        fixtures.install()
