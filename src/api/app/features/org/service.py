"""Organisation logic (F7). Team aggregates and plans come from the F5 pathway engine.

Only members whose intake is complete are counted; invited / in-progress members are listed
but excluded from the heatmap and plan until their skills are confirmed. Nothing here is
hard-coded: heatmap rows are every target role in the taxonomy, and when a manager has not
picked a target role the plan uses the role with the strongest existing team skill fit.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Sequence
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
    SharingIn,
    TeamSkillProgress,
    Workspace,
    WorkspaceList,
)
from app.contracts.pathway import Pathway
from app.contracts.profile import Skill
from app.core import accounts
from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.features.org import repository
from app.features.pathway import data as pathway_data
from app.features.pathway import engine
from app.features.pathway import repository as pathway_repository
from app.features.pathway import service as pathway_service
from app.features.profile import repository as profile_repository
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
    """Only an organisation's managers / advisors may see team data or change the setup.

    Members of a team never see colleagues' names, intake status, gaps or the group plan
    through the API, not only through the hidden /org pages.
    """
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
    """Join as an employee/student. Management rights are never granted by a join code, and one
    account may belong to several organisations, each its own workspace."""
    if not body.consent:
        raise AppError(
            "Consent is required to join an organisation.",
            status_code=400,
            code="consent_required",
        )
    # Sharing skill levels is a separate, optional choice (AGENTS.md §3.9): a member may join
    # without sharing and opt in later at /work/skills. The contract still requires an explicit
    # boolean, so a missing field is never read as consent.
    org = repository.find_org_by_code(body.code)
    if org is None:
        raise NotFoundError("That join code does not match any organisation.")
    if repository.membership_role(user.id, org.id) is not None:
        return org.model_copy(update={"join_code": None})  # rejoining is harmless
    has_skills = profile_service.has_profile(user.id) and bool(
        profile_service.get_my_profile(user.id).skills
    )
    repository.add_member(
        org.id,
        Member(
            id=user.id,
            display_name=user.display_name,
            current_role_id=None,
            intake_status="complete" if has_skills else "in_progress",
            skills_shared=body.share_skills,
        ),
    )
    account = accounts.find_by_id(user.id)
    if account is not None and not account.org_id:
        accounts.set_org(user.id, org.id)
    accounts.forget(user.id)
    return org.model_copy(update={"join_code": None})


def workspaces(user: CurrentUser) -> WorkspaceList:
    """Personal first, then every organisation the person belongs to."""
    items = [Workspace(id="personal", kind="personal", name="")]
    for org, role, shared in repository.memberships_of(user.id):
        items.append(
            Workspace(
                id=org.id,
                kind="org",
                name=org.name,
                org_type=org.type,
                role=role,
                skills_shared=shared,
            )
        )
    return WorkspaceList(workspaces=items)


def set_sharing(user: CurrentUser, body: SharingIn) -> Workspace:
    """A member chooses whether this organisation's managers may use their skill levels."""
    if user.workspace != "org" or not user.org_id or user.kind != "learner":
        raise AppError(
            "Open the organisation's workspace as a member to change sharing.",
            status_code=403,
            code="forbidden",
        )
    if not repository.set_share_skills(user.org_id, user.id, body.share_skills):
        raise NotFoundError("You are not a member of this organisation.")
    return next(w for w in workspaces(user).workspaces if w.id == user.org_id)


def require_manager(user: CurrentUser) -> str:
    """Public guard for other features' team endpoints (e.g. SDG contribution)."""
    return _require_manager(user)


def list_members(user: CurrentUser) -> MemberListResponse:
    return MemberListResponse(members=repository.list_members(_require_manager(user)))


def remove_member(user: CurrentUser, member_id: str) -> None:
    org_id = _require_manager(user)
    if not repository.remove_member(org_id, member_id):
        raise NotFoundError(f"No member {member_id} in this organisation")
    account = accounts.find_by_id(member_id)
    if account is not None and account.org_id == org_id:
        remaining = [o.id for o, _role, _shared in repository.memberships_of(member_id)]
        accounts.set_org(member_id, remaining[0] if remaining else None)
    accounts.forget(member_id)


def _learner_members(org_id: str, only: str | None = None) -> list[Member]:
    return [
        m
        for m in repository.list_members(org_id)
        if m.intake_status == "complete" and (m.id == only if only else m.skills_shared)
    ]


def _progress_scopes(org_id: str, members: Sequence[Member]) -> list[str]:
    """Personal records count only when every included member shared them."""
    scopes = [pathway_repository.org_scope(org_id)]
    if all(m.skills_shared for m in members):
        scopes.append(pathway_repository.PERSONAL)
    return scopes


def member_learners(org_id: str, only: str | None = None) -> dict[str, engine.Learner]:
    """Engine inputs for members with a completed intake (skills, time, budget only).

    Team views count only members who chose to share their skill levels. `only` reads one
    member for their own assignment, whatever they share with managers.
    """
    org = repository.get_org(org_id)
    company = org is not None and org.type == "company"
    out: dict[str, engine.Learner] = {}
    members = _learner_members(org_id, only)
    scopes = _progress_scopes(org_id, members)
    earned = pathway_service.evidenced_levels_many([m.id for m in members], scopes)
    profiles = profile_repository.get_profiles([m.id for m in members])
    for m in members:
        profile = profiles.get(m.id)
        if profile is None:
            continue
        out[m.id] = engine.Learner(
            skill_levels=pathway_service.combined_levels(
                m.id, {s.skill_id: s.level for s in profile.skills}, earned[m.id]
            ),
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


def target_role(
    org_id: str,
    role_id: str | None = None,
    *,
    members: dict[str, engine.Learner] | None = None,
) -> str:
    """The manager's chosen role, else the role with the strongest existing team skill fit."""
    roles = pathway_data.target_role_ids()
    if role_id:
        if role_id not in roles:
            raise NotFoundError(f"Unknown target role {role_id}")
        return role_id
    if not roles:
        raise NotFoundError("No target roles in the taxonomy")
    team = member_learners(org_id) if members is None else members

    def fit(role: str) -> tuple[float, str]:
        reqs = pathway_data.requirements(role)
        total = sum(r.importance for r in reqs) * len(team)
        covered = sum(
            r.importance * min(1.0, learner.skill_levels.get(r.skill_id, 0) / r.required_level)
            for learner in team.values()
            for r in reqs
        )
        return (covered / total if total else 0.0, role)

    return max(roles, key=fit)


def member_plans(
    org_id: str, scenario: ScenarioId, role_id: str | None = None
) -> dict[str, Pathway]:
    """Each counted member's own pathway towards the organisation's target role (F6 uses it)."""
    members = member_learners(org_id)
    role = target_role(org_id, role_id, members=members)
    return {
        mid: pathway_service.build_pathway(learner, role, scenario)
        for mid, learner in members.items()
    }


def _team_learning_progress(
    org_id: str, member_ids: list[str], min_cohort: int
) -> list[TeamSkillProgress]:
    """Self-reported course counts, only for consenting members and this employer's routes.

    Suppression applies to each skill's participating cohort, not just the whole team.
    No personal or other employer records are read.
    """
    from app.features.org import funding_store
    from app.features.pathway import verification

    rows = pathway_repository.learning_records(member_ids, [pathway_repository.org_scope(org_id)])
    done = {
        (r.user_id, r.role_id, r.course_id)
        for r in rows
        if verification.effective_statuses(
            {r.course_id: r.status}, {r.course_id: r.evidence} if r.evidence else {}
        ).get(r.course_id)
        == "completed"
    }
    planned: dict[str, set[tuple[str, str]]] = {}
    completed: dict[str, set[tuple[str, str]]] = {}
    seen: set[tuple[str, str]] = set()
    for assignment in reversed(funding_store.snapshot(org_id).assignments):
        uid, rid = assignment.user_id, assignment.agreement.role_id
        if uid not in member_ids or assignment.status != "accepted" or (uid, rid) in seen:
            continue
        seen.add((uid, rid))
        for step in assignment.pathway.steps:
            for course in step.courses:
                key = (uid, course.id)
                planned.setdefault(step.skill_id, set()).add(key)
                if (uid, rid, course.id) in done:
                    completed.setdefault(step.skill_id, set()).add(key)
    labels = pathway_data.skill_labels()
    result = []
    for sid, courses in sorted(planned.items()):
        cohort = len({uid for uid, _cid in courses})
        hidden = cohort < min_cohort
        result.append(
            TeamSkillProgress(
                skill_id=sid,
                label=labels.get(sid, sid),
                cohort_size=cohort,
                planned_courses=None if hidden else len(courses),
                completed_courses=None if hidden else len(completed.get(sid, set())),
                suppressed=hidden,
            )
        )
    return result


def get_gaps(user: CurrentUser, scenario: ScenarioId) -> GapHeatmapResponse:
    org_id = _require_manager(user)
    members = member_learners(org_id)
    observed = profile_repository.observed_on(
        list(members), _progress_scopes(org_id, _learner_members(org_id))
    )
    labels = pathway_data.skill_labels()
    roles = pathway_data.target_role_ids()
    min_cohort = get_settings().org_min_cohort
    suppressed = len(members) < min_cohort
    computed = pathway_service.team_gaps(members, roles)
    skill_ids = list(dict.fromkeys(skill for _, skill, _ in computed))
    by_cell = {(role, skill): gap for role, skill, gap in computed}
    required: dict[str, list[float]] = {r: [] for r in roles}
    for role, _skill, gap in computed:
        required[role].append(gap)
    cells = [
        {
            "role_id": role,
            "skill_id": skill,
            "gap": None if suppressed else by_cell.get((role, skill), 0.0),
            "suppressed": suppressed,
        }
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
            "cohort_size": len(members),
            "min_cohort": min_cohort,
            "learning_progress": _team_learning_progress(org_id, list(members), min_cohort),
            "role_suppressed": {r: suppressed for r in roles},
            "role_gaps": {
                r: None if suppressed else (round(sum(v) / len(v), 4) if v else 0.0)
                for r, v in required.items()
            },
            "meta": RecommendationMeta(
                sources=[TEAM_DATA_SOURCE]
                + (
                    [
                        Source(
                            name="Consenting member learning records",
                            url="https://github.com/pecel-lelele/adept/blob/main/src/api/app/features/org/service.py",
                            retrieved_at=observed,
                        )
                    ]
                    if observed
                    else []
                ),
                snapshot_date=observed or TEAM_DATA_SOURCE.retrieved_at,
                scenario=scenario,
                is_estimate=False,
            ),
        }
    )


def require_cohort(size: int) -> None:
    """Gate team-derived disclosures, including explicitly selected subsets."""
    minimum = get_settings().org_min_cohort
    if size < minimum:
        raise AppError(
            f"Too few members: at least {minimum} sharing members with completed profiles "
            "are required for team planning.",
            status_code=409,
            code="insufficient_cohort",
        )


def get_plan(user: CurrentUser, scenario: ScenarioId, role_id: str | None = None) -> GroupPlan:
    org_id = _require_manager(user)
    org = repository.get_org(org_id)
    members = member_learners(org_id)
    require_cohort(len(members))
    pathway = pathway_service.group_pathway(
        members,
        target_role(org_id, role_id, members=members),
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
