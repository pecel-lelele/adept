"""Data access for matching. Reads mocks; later `roles`, `role_skills`, `user_skills`."""

from app.contracts.common import ScenarioId
from app.contracts.matching import RoleMatch
from app.features.matching import mocks


def list_matches(user_id: str, scenario: ScenarioId) -> list[RoleMatch]:
    return mocks.matches(scenario)


def get_match(user_id: str, role_id: str, scenario: ScenarioId) -> RoleMatch | None:
    return mocks.match(role_id, scenario)
