"""Organisation logic (F7). Team aggregates and plans come from the F5 pathway engine.

Only members whose intake is complete are counted; invited / in-progress members are listed
but excluded from the heatmap and plan until their skills are confirmed. Nothing here is
hard-coded: heatmap rows are every target role in the taxonomy, and when a manager has not
picked a target role the plan uses the role where the team's average gap is largest.
"""

from __future__ import annotations

import re
import secrets
from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.org import (
    GapHeatmapResponse,
    GroupPlan,
    JoinOrgIn,
    Member,
    MemberListResponse,
    Organization,
    OrganizationIn,
)
from app.contracts.pathway import Pathway
from app.contracts.profile import Skill
from app.core import accounts
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.org import repository
from app.features.pathway import data as pathway_data
from app.features.pathway import engine
from app.features.pathway import service as pathway_service
from app.features.profile import service as profile_service

TEAM_DATA_SOURCE = Source(
    name="Member skill profiles + Adept role requirements",
    url="https://github.com/pecel-lelele/adept/blob/main/src/data/seed/taxonomy/role_skills.csv",
    retrieved_at=date(2026, 10, 20),
)


def _org_id(user: CurrentUser) -> str:
    if not user.org_id:
        raise NotFoundError("You are not part of an organisation yet.")
    return user.org_id


def _require_manager(user: CurrentUser) -> str:
    """Only an organisation's managers / advisors may change its setup or membership."""
    if user.kind != "org_admin":
        raise AppError(
            "Only organisation managers can change this.", status_code=403, code="forbidden"
        )
    return _org_id(user)


def new_org_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:32] or "org"
    return f"org-{slug}-{secrets.token_hex(3)}"


def _visible(org: Organization, user: CurrentUser) -> Organization:
    return org if user.kind == "org_admin" else org.model_copy(update={"join_code": None})


def get_my_org(user: CurrentUser) -> Organization:
    org = repository.get_org(_org_id(user))
    if org is None:
        raise NotFoundError("Organisation not found")
    return _visible(org, user)


def create_org(owner: accounts.Account, data: OrganizationIn) -> Organization:
    org = Organization(
        id=new_org_id(data.name),
        type=data.type,
        name=" ".join(data.name.split()),
        industry=" ".join(data.industry.split()),
        size=data.size,
        join_code=repository.new_join_code(),
    )
    role = "manager" if data.type == "company" else "advisor"
    repository.create_org(org, owner.id, role)
    accounts.set_org(owner.id, org.id)
    return org


def update_my_org(user: CurrentUser, data: OrganizationIn) -> Organization:
    org_id = _require_manager(user)
    current = repository.get_org(org_id)
    if current is None:
        raise NotFoundError("Organisation not found")
    updated = current.model_copy(
        update={
            "type": data.type,
            "name": " ".join(data.name.split()),
            "industry": " ".join(data.industry.split()),
            "size": data.size,
        }
    )
    return repository.update_org(updated)


def rotate_join_code(user: CurrentUser) -> Organization:
    org_id = _require_manager(user)
    repository.set_join_code(org_id, repository.new_join_code())
    return get_my_org(user)


def join_org(user: CurrentUser, body: JoinOrgIn) -> Organization:
    if user.kind == "org_admin":
        raise AppError(
            "Manager accounts already belong to an organisation.", status_code=409, code="conflict"
        )
    org = repository.find_org_by_code(body.code)
    if org is None:
        raise NotFoundError("That join code does not match any organisation.")
    current = accounts.find_by_id(user.id)
    if current is not None and current.org_id and current.org_id != org.id:
        # One organisation per member: a second join would be saved but never shown.
        raise AppError(
            "You already belong to an organisation. Ask its manager to remove you first.",
            status_code=409,
            code="already_member",
        )
    has_skills = profile_service.has_profile(user.id) and bool(
        profile_service.get_my_profile(user).skills
    )
    repository.add_member(
        org.id,
        Member(
            id=user.id,
            display_name=user.display_name,
            current_role_id=None,
            intake_status="complete" if has_skills else "in_progress",
        ),
    )
    accounts.set_org(user.id, org.id)
    return _visible(org, user)


def list_members(user: CurrentUser) -> MemberListResponse:
    return MemberListResponse(members=repository.list_members(_org_id(user)))


def remove_member(user: CurrentUser, member_id: str) -> None:
    org_id = _require_manager(user)
    if not repository.remove_member(org_id, member_id):
        raise NotFoundError(f"No member {member_id} in this organisation")
    accounts.set_org(member_id, None)


def member_learners(org_id: str) -> dict[str, engine.Learner]:
    """Engine inputs for members with a completed intake (skills, time, budget only)."""
    org = repository.get_org(org_id)
    company = org is not None and org.type == "company"
    out: dict[str, engine.Learner] = {}
    for m in repository.list_members(org_id):
        if m.intake_status != "complete":
            continue
        profile = profile_service.get_my_profile(m.id)
        out[m.id] = engine.Learner(
            skill_levels={s.skill_id: s.level for s in profile.skills},
            hours_per_week=float(profile.hours_per_week),
            budget_myr=float(profile.budget_myr),
            # Company plans can use the employer's HRD Corp levy; institutions cannot.
            hrd_eligible=company or profile.hrd_eligible,
        )
    return out


def _team_gap_by_role(members: dict[str, engine.Learner]) -> dict[str, float]:
    roles = pathway_data.target_role_ids()
    totals: dict[str, list[float]] = {r: [] for r in roles}
    for role, _skill, gap in pathway_service.team_gaps(members, roles):
        totals[role].append(gap)
    return {r: (sum(v) / len(v) if v else 0.0) for r, v in totals.items()}


def target_role(org_id: str, role_id: str | None = None) -> str:
    """The manager's chosen role, else the role where the team's average gap is largest."""
    roles = pathway_data.target_role_ids()
    if role_id:
        if role_id not in roles:
            raise NotFoundError(f"Unknown target role {role_id}")
        return role_id
    if not roles:
        raise NotFoundError("No target roles in the taxonomy")
    gaps = _team_gap_by_role(member_learners(org_id))
    return max(roles, key=lambda r: (gaps.get(r, 0.0), r))


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
    roles = pathway_data.target_role_ids()
    computed = pathway_service.team_gaps(members, roles)
    skill_ids = list(dict.fromkeys(skill for _, skill, _ in computed))
    by_cell = {(role, skill): gap for role, skill, gap in computed}
    required: dict[str, list[float]] = {r: [] for r in roles}
    for role, _skill, gap in computed:
        required[role].append(gap)
    cells = [
        {"role_id": role, "skill_id": skill, "gap": by_cell.get((role, skill), 0.0)}
        for role in roles
        for skill in skill_ids
    ]
    return GapHeatmapResponse.model_validate(
        {
            "role_ids": roles,
            "role_labels": {r: pathway_data.role_labels().get(r, r) for r in roles},
            "skills": [Skill(id=s, label=labels.get(s, s)) for s in skill_ids],
            "cells": cells,
            # Same average as _team_gap_by_role, so the page ranks roles like the backend.
            "role_gaps": {r: round(sum(v) / len(v), 4) if v else 0.0 for r, v in required.items()},
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
        target_role_label=pathway.role_label or pathway.role_id,
        assigned_member_ids=assigned,
        steps=pathway.steps,
        total_weeks=pathway.total_weeks,
        meta=pathway.meta,
    )
