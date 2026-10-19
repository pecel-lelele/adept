"""Data access for scenarios. Reads mocks for now."""

from app.contracts.scenarios import RoleOutlook, Scenario
from app.features.scenarios import mocks


def list_scenarios() -> list[Scenario]:
    return mocks.SCENARIOS


def list_outlooks(role_id: str | None) -> list[RoleOutlook]:
    return mocks.outlooks(role_id)
