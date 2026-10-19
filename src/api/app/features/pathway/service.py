"""Pathway logic (F5). Ordering and time estimation are open choices for M3."""

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.pathway import Pathway
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.pathway import repository

DEMO_HOURS_PER_WEEK = 6  # Aisyah's budget; TODO(F5): read from the user's profile.


def get_pathway(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Pathway:
    steps = repository.build_steps(role_id, DEMO_HOURS_PER_WEEK)
    if not steps:
        raise NotFoundError(f"No pathway for role {role_id}")
    return Pathway(
        role_id=role_id,
        steps=steps,
        total_weeks=steps[-1].week_end,
        meta=mock_meta(scenario),
    )
