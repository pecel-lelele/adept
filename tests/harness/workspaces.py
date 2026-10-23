"""Test helpers for organisation workspaces: an accepted work programme without the HR flow."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.contracts.funding import FundingState
from app.contracts.pathway import Pathway
from app.contracts.programmes import Agreement, ProgrammeAssignment
from app.core.auth import CurrentUser
from app.features.org import funding, funding_store
from app.features.pathway import service as pathway_service

BANK = "org-demo-bank"


def work_headers(user_id: str = "aisyah", org_id: str = BANK) -> dict[str, str]:
    """Headers for a member acting in their organisation's workspace."""
    return {"X-Demo-User": user_id, "X-Workspace": org_id}


def accept_work_plan(
    role_id: str, user_id: str = "aisyah", org_id: str = BANK, programme_id: str = "prog-test"
) -> Pathway:
    """Store an accepted programme route for `role_id`, as if HR sent it and the member agreed."""
    user = CurrentUser(user_id, user_id, "learner", None, "personal")
    pathway = pathway_service.get_pathway(user, role_id, "moderate")
    now = datetime.now(UTC)
    agreement = Agreement(
        programme_id=programme_id,
        title="Test programme",
        objectives=["ai_adoption"],
        role_id=role_id,
        role_label=pathway.role_label or role_id,
        route="applied",
        readiness=0.5,
        mandatory=False,
        target_date=date.today() + timedelta(weeks=12),
        hours_per_week=4,
        budget_myr=pathway.total_cost_myr,
        cost_myr=pathway.total_cost_myr,
        sent_at=now,
        sent_by="demo-company",
    )
    assignment = ProgrammeAssignment(
        agreement=agreement, user_id=user_id, pathway=pathway, status="accepted", decided_at=now
    )

    def add(state: FundingState) -> None:
        state.assignments.append(assignment)

    funding_store.transact(org_id, funding.current_year(), add)
    return pathway
