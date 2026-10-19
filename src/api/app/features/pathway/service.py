"""Pathway service (F5): builds plans from the learner's profile, the course catalogue and the
latest trend snapshot; saves the plan the learner chooses; proposes re-plans; tracks progress.

Public functions other features may call: `get_pathway`, `build_pathway`, `learner_for`,
`group_pathway`, `team_gaps`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Literal

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.pathway import (
    Badge,
    CatalogueResponse,
    Course,
    Pathway,
    PathwayStep,
    Progress,
    ProgressUpdate,
    ReplanStatus,
    SavedPlan,
    SavePlanIn,
)
from app.contracts.sdg import SdgTarget
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.pathway import data, engine, progress, replan, repository
from app.features.profile import service as profile_service
from app.features.sdg import repository as sdg_repository

CATALOGUE_SOURCE_FALLBACK = "Adept course catalogue"


# --- building ------------------------------------------------------------------


def learner_for(user: CurrentUser) -> engine.Learner:
    """Only skills, time, budget and HRD Corp eligibility; never identity (fairness)."""
    profile = profile_service.get_my_profile(user)
    return engine.Learner(
        skill_levels={s.skill_id: s.level for s in profile.skills},
        hours_per_week=float(profile.hours_per_week),
        budget_myr=float(profile.budget_myr),
        hrd_eligible=profile.hrd_eligible,
    )


def _sdg_by_skill(skill_ids: Sequence[str]) -> dict[str, list[SdgTarget]]:
    return {s: [link.target for link in sdg_repository.skill_links(s)] for s in skill_ids}


def _meta(
    steps: Sequence[PathwayStep], snapshot: data.Snapshot | None, scenario: ScenarioId
) -> RecommendationMeta:
    sources: dict[str, Source] = {}
    for step in steps:
        for course in step.courses:
            src = course.source or Source(
                name=CATALOGUE_SOURCE_FALLBACK, url=course.url, retrieved_at=course.verified_at
            )
            prev = sources.get(src.name)
            if prev is None or src.retrieved_at < prev.retrieved_at:
                sources[src.name] = src  # oldest verification date is the honest one
    if snapshot:
        sources.setdefault(snapshot.source.name, snapshot.source)
    if not sources:
        courses = data.catalogue()
        oldest = min((c.verified_at for c in courses), default=date.today())
        sources[CATALOGUE_SOURCE_FALLBACK] = Source(
            name=CATALOGUE_SOURCE_FALLBACK,
            url="https://github.com/pecel-lelele/adept/blob/main/src/data/seed/courses/courses.csv",
            retrieved_at=oldest,
        )
    if snapshot:
        snapshot_date = snapshot.source.retrieved_at
    else:
        snapshot_date = min(s.retrieved_at for s in sources.values())
    return RecommendationMeta(
        sources=list(sources.values()),
        snapshot_date=snapshot_date,
        scenario=scenario,
        is_estimate=True,
    )


def build_pathway(
    learner: engine.Learner,
    role_id: str,
    scenario: ScenarioId,
    snapshot: data.Snapshot | None = None,
    catalogue: Sequence[Course] | None = None,
) -> Pathway:
    reqs = data.requirements(role_id)
    labels = data.role_labels()
    if role_id not in labels or not reqs:
        raise NotFoundError(f"No pathway for role {role_id}")
    snapshot = snapshot or data.latest_snapshot()
    growth = data.skill_growth(snapshot.id) if snapshot else {}
    plan = engine.build(
        reqs,
        learner,
        scenario,
        catalogue if catalogue is not None else data.catalogue(),
        data.prerequisites(),
        growth,
        data.skill_labels(),
        _sdg_by_skill([r.skill_id for r in reqs]),
    )
    return Pathway(
        role_id=role_id,
        role_label=labels[role_id],
        steps=plan.steps,
        total_weeks=plan.total_weeks,
        meta=_meta(plan.steps, snapshot, scenario),
        hours_per_week=plan.hours_per_week,
        total_hours=plan.total_hours,
        total_cost_myr=plan.total_cost_myr,
        out_of_pocket_myr=plan.out_of_pocket_myr,
        budget_myr=learner.budget_myr,
        within_budget=plan.out_of_pocket_myr <= learner.budget_myr,
        hrd_eligible=learner.hrd_eligible,
        gaps=plan.gaps,
        unmet=plan.unmet,
        warnings=plan.warnings,
        snapshot_version=snapshot.version if snapshot else "",
    )


def get_pathway(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Pathway:
    return build_pathway(learner_for(user), role_id, scenario)


def catalogue() -> CatalogueResponse:
    courses = data.catalogue()
    step = PathwayStep(
        order=1, skill_id="-", courses=courses, est_hours=0, week_start=1, week_end=1, reason=""
    )
    meta = _meta([step], None, "moderate").model_copy(update={"is_estimate": False})
    return CatalogueResponse(courses=courses, meta=meta)


# --- saved plans and re-planning ---------------------------------------------------


def save_plan(user: CurrentUser, body: SavePlanIn) -> SavedPlan:
    """The learner's explicit choice of target role (human in charge)."""
    pathway = get_pathway(user, body.role_id, body.scenario)
    plan = SavedPlan(
        role_id=body.role_id,
        scenario=body.scenario,
        snapshot_version=pathway.snapshot_version,
        saved_at=datetime.now(UTC),
        pathway=pathway,
    )
    return repository.save_plan(user.id, plan)


def get_saved_plan(user: CurrentUser) -> SavedPlan | None:
    return repository.get_plan(user.id)


def replan_status(user: CurrentUser) -> ReplanStatus:
    saved = repository.get_plan(user.id)
    latest = data.latest_snapshot()
    latest_version = latest.version if latest else ""
    if saved is None:
        return ReplanStatus(
            saved=None,
            latest_snapshot_version=latest_version,
            needs_replan=False,
            changes=[],
            proposed=None,
            message="No saved plan yet. Choose a target role and save its pathway.",
            meta=_meta([], latest, "moderate"),
        )
    proposed = get_pathway(user, saved.role_id, saved.scenario)
    changes = replan.diff_plans(saved.pathway, proposed)
    newer = saved.snapshot_version != latest_version
    needs = bool(changes) and newer
    if needs and latest:
        message = (
            f"New trend data ({latest.source.name}, {latest.source.retrieved_at}) changes "
            f"{len(changes)} part(s) of your plan. Review and accept, or keep your current plan."
        )
    elif newer:
        message = f"Checked against trend snapshot {latest_version}: your plan is unchanged."
    else:
        message = "Your plan uses the latest trend snapshot."
    return ReplanStatus(
        saved=saved,
        latest_snapshot_version=latest_version,
        needs_replan=needs,
        changes=changes,
        proposed=proposed if needs else None,
        message=message,
        meta=proposed.meta,
    )


def accept_replan(user: CurrentUser) -> SavedPlan:
    saved = repository.get_plan(user.id)
    if saved is None:
        raise NotFoundError("No saved plan to re-plan")
    return save_plan(user, SavePlanIn(role_id=saved.role_id, scenario=saved.scenario))


# --- progress and badges --------------------------------------------------------------


def _plan_for_progress(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Pathway:
    saved = repository.get_plan(user.id)
    if saved and saved.role_id == role_id:
        return saved.pathway
    return get_pathway(user, role_id, scenario)


def _badge_label(
    badge_id: str, labels: Mapping[str, str]
) -> tuple[Literal["skill", "milestone"], str | None, str]:
    kind, _, key = badge_id.partition(":")
    if kind == "skill":
        return "skill", key, f"{labels.get(key, key)} at target level"
    names = {"first": "First course done", "halfway": "Halfway there", "complete": "Plan complete"}
    return "milestone", None, names.get(key, key)


def get_progress(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Progress:
    plan = _plan_for_progress(user, role_id, scenario)
    statuses = repository.course_status(user.id, role_id)
    index = data.course_index()
    levels = {cid: {s: c.level for s in c.skill_ids} for cid, c in index.items()}
    skills = progress.skill_progress(plan, statuses, levels)
    earned = repository.record_badges(
        user.id, progress.earned_badges(plan, statuses, skills), date.today()
    )
    labels = data.skill_labels()
    badges = []
    for badge_id, earned_at in sorted(earned.items()):
        kind, skill_id, label = _badge_label(badge_id, labels)
        badges.append(
            Badge(id=badge_id, kind=kind, label=label, earned_at=earned_at, skill_id=skill_id)
        )
    return Progress(
        role_id=role_id,
        course_status=statuses,
        percent_complete=progress.percent_complete(plan, statuses),
        skills=skills,
        gap_closed=sum(1 for s in skills if s.closed),
        gap_total=len(skills),
        badges=badges,
        meta=plan.meta,
    )


def update_progress(user: CurrentUser, body: ProgressUpdate, scenario: ScenarioId) -> Progress:
    plan = _plan_for_progress(user, body.role_id, scenario)
    if body.course_id not in progress.planned_courses(plan):
        raise AppError(
            f"Course {body.course_id} is not in your plan for {body.role_id}",
            status_code=422,
            code="unknown_course",
        )
    repository.set_course_status(user.id, body.role_id, body.course_id, body.status)
    return get_progress(user, body.role_id, scenario)


# --- teams (F7 uses these) ----------------------------------------------------------------


def group_pathway(
    members: Mapping[str, engine.Learner],
    role_id: str,
    scenario: ScenarioId,
    hrd_eligible: bool,
    budget_myr: float = float("inf"),
) -> Pathway:
    """One plan for a team: each skill starts from the weakest member who needs it, and each
    step lists the members who need it (`member_ids`). Hours/week = the team's median."""
    reqs = data.requirements(role_id)
    hours = sorted(m.hours_per_week for m in members.values() if m.hours_per_week > 0)
    weakest = {
        r.skill_id: min((m.skill_levels.get(r.skill_id, 0) for m in members.values()), default=0)
        for r in reqs
    }
    team = engine.Learner(
        skill_levels=weakest,
        hours_per_week=hours[len(hours) // 2] if hours else 0,
        budget_myr=budget_myr,
        hrd_eligible=hrd_eligible,
    )
    plan = build_pathway(team, role_id, scenario)
    need = {r.skill_id: r.required_level for r in reqs}
    steps = [
        s.model_copy(
            update={
                "member_ids": sorted(
                    mid
                    for mid, m in members.items()
                    if m.skill_levels.get(s.skill_id, 0) < need[s.skill_id]
                )
            }
        )
        for s in plan.steps
    ]
    budget = plan.budget_myr if budget_myr != float("inf") else 0
    return plan.model_copy(update={"steps": steps, "budget_myr": budget})


def team_gaps(
    members: Mapping[str, engine.Learner], role_ids: Sequence[str]
) -> list[tuple[str, str, float]]:
    """(role, skill, share of members below the required level) for a heatmap."""
    out: list[tuple[str, str, float]] = []
    n = len(members)
    for role_id in role_ids:
        for r in data.requirements(role_id):
            levels = [m.skill_levels.get(r.skill_id, 0) for m in members.values()]
            below = sum(1 for level in levels if level < r.required_level)
            out.append((role_id, r.skill_id, round(below / n, 2) if n else 0.0))
    return out
