"""Data access for SDG links. Reads mocks; later `sdg_targets`, `role_sdg_map`, `skill_sdg_map`."""

from app.contracts.sdg import SdgLink
from app.features.sdg import mocks


def role_links(role_id: str) -> list[SdgLink]:
    return mocks.links(mocks.ROLE_LINKS, role_id)


def skill_links(skill_id: str) -> list[SdgLink]:
    return mocks.links(mocks.SKILL_LINKS, skill_id)
