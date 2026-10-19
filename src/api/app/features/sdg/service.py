"""SDG logic (F6). Mapping method and review process are open choices for M3."""

from app.contracts.common import mock_meta
from app.contracts.sdg import EntitySdgLinks, SdgContribution
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.sdg import mocks, repository

# TODO(F6): derive from the user's chosen target role and pathway skills.
DEMO_ROLE_ID = "data-analyst"
DEMO_SKILL_IDS = ["sql", "python"]


def role_sdg(role_id: str) -> EntitySdgLinks:
    links = repository.role_links(role_id)
    if not links:
        raise NotFoundError(f"No SDG links for role {role_id}")
    return EntitySdgLinks(entity_type="role", entity_id=role_id, links=links, meta=mock_meta())


def skill_sdg(skill_id: str) -> EntitySdgLinks:
    links = repository.skill_links(skill_id)
    if not links:
        raise NotFoundError(f"No SDG links for skill {skill_id}")
    return EntitySdgLinks(entity_type="skill", entity_id=skill_id, links=links, meta=mock_meta())


def my_contribution(user: CurrentUser) -> SdgContribution:
    links = repository.role_links(DEMO_ROLE_ID)
    for skill_id in DEMO_SKILL_IDS:
        links += repository.skill_links(skill_id)
    return SdgContribution(goals_summary=mocks.summarise(links), links=links, meta=mock_meta())
