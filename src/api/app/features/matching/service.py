"""Matching logic (F4). Scoring formula, weights and fairness tests are open choices for M2."""

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.matching import MatchResponse, RoleMatch
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.matching import repository


def list_matches(user: CurrentUser, scenario: ScenarioId) -> MatchResponse:
    return MatchResponse(
        matches=repository.list_matches(user.id, scenario), meta=mock_meta(scenario)
    )


def get_match(user: CurrentUser, role_id: str, scenario: ScenarioId) -> RoleMatch:
    match = repository.get_match(user.id, role_id, scenario)
    if match is None:
        raise NotFoundError(f"No match for role {role_id}")
    return match
