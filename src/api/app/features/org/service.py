"""Organisation logic (F7). Team aggregates and plans come from the F5 pathway engine.

Only members whose intake is complete are counted; invited / in-progress members are listed
but excluded from the heatmap and plan until their skills are confirmed.
"""

from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.org import GapHeatmapResponse, GroupPlan, MemberListResponse, Organization
from app.contracts.pathway import Pathway
from app.contracts.profile import Skill
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.org import mocks, repository
from app.features.pathway import data as pathway_data
from app.features.pathway import engine
from app.features.pathway import service as pathway_service
from app.features.profile import service as profile_service

DEFAULT_ORG_ID = "org-demo-bank"
TEAM_DATA_SOURCE = Source(
    name="Member skill profiles (synthetic) + Adept role requirements",
    url="https://github.com/pecel-lelele/adept/blob/main/src/data/seed/taxonomy/role_skills.csv",
    retrieved_at=date(2026, 10, 20),
)


def _org_id(user: CurrentUser) -> str:
    return user.org_id or DEFAULT_ORG_ID


def get_my_org(user: CurrentUser) -> Organization:
    org = repository.get_org(_org_id(user))
    if org is None:
        raise NotFoundError("Organisation not found")
    return org


def list_members(user: CurrentUser) -> MemberListResponse:
    return MemberListResponse(members=repository.list_members(_org_id(user)))


def member_learners(org_id: str) -> dict[str, engine.Learner]:
    """Engine inputs for members with a completed intake (skills, time, budget only)."""
    org = repository.get_org(org_id)
    company = org is not None and org.type == "company"
    out: dict[str, engine.Learner] = {}
    for m in repository.list_members(org_id):
        if m.intake_status != "complete":
            continue
        profile = profile_service.get_my_profile(CurrentUser(m.id, m.display_name, "learner"))
        levels = {s.skill_id: s.level for s in profile.skills} or mocks.TEAM_SKILLS.get(m.id, {})
        out[m.id] = engine.Learner(
            skill_levels=levels,
            hours_per_week=float(profile.hours_per_week),
            budget_myr=float(profile.budget_myr),
            # Company plans can use the employer's HRD Corp levy; institutions cannot.
            hrd_eligible=company or profile.hrd_eligible,
        )
    return out


def target_role(org_id: str, role_id: str | None = None) -> str:
    return role_id or mocks.DEFAULT_TARGET_ROLE.get(org_id, "data-analyst")


def member_plans(
    org_id: str, scenario: ScenarioId, role_id: str | None = None
) -> dict[str, Pathway]:
    """Each counted member's own pathway towards the organisation's target role (F6 uses it)."""
    role = target_role(org_id, role_id)
    return {
        mid: pathway_service.build_pathway(learner, role, scenario)
        for mid, learner in member_learners(org_id).items()
    }


def get_gaps(user: CurrentUser, scenario: ScenarioId) -> GapHeatmapResponse:
    members = member_learners(_org_id(user))
    labels = pathway_data.skill_labels()
    computed = pathway_service.team_gaps(members, mocks.GAP_ROLES)
    skill_ids = list(dict.fromkeys(skill for _, skill, _ in computed))
    by_cell = {(role, skill): gap for role, skill, gap in computed}
    cells = [
        {"role_id": role, "skill_id": skill, "gap": by_cell.get((role, skill), 0.0)}
        for role in mocks.GAP_ROLES
        for skill in skill_ids
    ]
    return GapHeatmapResponse.model_validate(
        {
            "role_ids": mocks.GAP_ROLES,
            "skills": [Skill(id=s, label=labels.get(s, s)) for s in skill_ids],
            "cells": cells,
            "meta": RecommendationMeta(
                sources=[TEAM_DATA_SOURCE],
                snapshot_date=TEAM_DATA_SOURCE.retrieved_at,
                scenario=scenario,
                is_estimate=False,
            ),
        }
    )


def get_plan(user: CurrentUser, scenario: ScenarioId, role_id: str | None = None) -> GroupPlan:
    org_id = _org_id(user)
    org = repository.get_org(org_id)
    members = member_learners(org_id)
    pathway = pathway_service.group_pathway(
        members,
        target_role(org_id, role_id),
        scenario,
        hrd_eligible=org is not None and org.type == "company",
    )
    assigned = sorted({mid for step in pathway.steps for mid in step.member_ids})
    return GroupPlan(
        org_id=org_id,
        target_role_id=pathway.role_id,
        assigned_member_ids=assigned,
        steps=pathway.steps,
        total_weeks=pathway.total_weeks,
        meta=pathway.meta,
    )
