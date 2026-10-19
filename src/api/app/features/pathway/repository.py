"""Data access for pathways. Reads mocks; later `courses` and a prerequisite graph."""

from app.contracts.pathway import PathwayStep
from app.features.pathway import mocks


def build_steps(role_id: str, hours_per_week: int) -> list[PathwayStep]:
    return mocks.steps(role_id, hours_per_week)
