"""Data access for organisations. Reads mocks; later `organizations` and `memberships`."""

from app.contracts.org import GapHeatmapCell, Member, Organization
from app.features.org import mocks


def get_org(org_id: str) -> Organization | None:
    return mocks.ORGS.get(org_id)


def list_members(org_id: str) -> list[Member]:
    return mocks.MEMBERS.get(org_id, [])


def gap_cells(widen: float) -> list[GapHeatmapCell]:
    return mocks.heatmap(widen)
