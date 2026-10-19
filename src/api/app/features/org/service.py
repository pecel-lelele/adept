"""Organisation logic (F7). Team aggregates will come from F4 matching; plans from F5."""

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.org import GapHeatmapResponse, GroupPlan, MemberListResponse, Organization
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.org import mocks, repository
from app.features.pathway import service as pathway_service

DEFAULT_ORG_ID = "org-demo-bank"
DEMO_TARGET_ROLE_ID = "data-analyst"
SCENARIO_GAP_FACTOR: dict[ScenarioId, float] = {"moderate": 1.0, "fast": 1.15}


def _org_id(user: CurrentUser) -> str:
    return user.org_id or DEFAULT_ORG_ID


def get_my_org(user: CurrentUser) -> Organization:
    org = repository.get_org(_org_id(user))
    if org is None:
        raise NotFoundError("Organisation not found")
    return org


def list_members(user: CurrentUser) -> MemberListResponse:
    return MemberListResponse(members=repository.list_members(_org_id(user)))


def get_gaps(user: CurrentUser, scenario: ScenarioId) -> GapHeatmapResponse:
    return GapHeatmapResponse(
        role_ids=mocks.GAP_ROLES,
        skills=mocks.GAP_SKILLS,
        cells=repository.gap_cells(SCENARIO_GAP_FACTOR[scenario]),
        meta=mock_meta(scenario),
    )


def get_plan(user: CurrentUser, scenario: ScenarioId) -> GroupPlan:
    org_id = _org_id(user)
    # Reuses F5's public service; TODO(F7): let the manager pick the target role.
    pathway = pathway_service.get_pathway(user, DEMO_TARGET_ROLE_ID, scenario)
    return GroupPlan(
        org_id=org_id,
        target_role_id=pathway.role_id,
        assigned_member_ids=[m.id for m in repository.list_members(org_id)],
        steps=pathway.steps,
        total_weeks=pathway.total_weeks,
        meta=pathway.meta,
    )
