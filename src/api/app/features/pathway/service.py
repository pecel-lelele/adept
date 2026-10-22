"""Pathway service (F5): builds plans from the learner's profile, the course catalogue and the
latest trend snapshot; saves the plan the learner chooses; proposes re-plans; tracks progress.

Public functions other features may call: `get_pathway`, `build_pathway`, `learner_for`,
`group_pathway`, `team_gaps`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.pathway import (
    Badge,
    CatalogueResponse,
    CompletionEvidence,
    Course,
    EvidenceSubmit,
    Pathway,
    PathwayStep,
    Progress,
    ProgressUpdate,
    ReplanStatus,
    ReviewDecision,
    RoleComparison,
    RoleOption,
    SavedPlan,
    SavePlanIn,
    VerificationItem,
    VerificationQueue,
)
from app.contracts.profile import Profile
from app.contracts.sdg import SdgTarget
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError, ProfileRequiredError
from app.features.org import repository as org_repository
from app.features.pathway import (
    data,
    engine,
    progress,
    replan,
    repository,
    trend_port,
    verification,
)
from app.features.profile import service as profile_service
from app.features.sdg import repository as sdg_repository

CATALOGUE_SOURCE_FALLBACK = "Adept course catalogue"


# --- building ------------------------------------------------------------------


def learner_for(user: CurrentUser) -> engine.Learner:
    """Only skills, time, budget and HRD Corp eligibility; never identity (fairness).

    A plan needs a saved profile (same rule as matching): planning for an empty profile would
    show weeks and costs for skills the learner was never asked about."""
    if not profile_service.has_profile(user.id):
        raise ProfileRequiredError()
    return _learner(profile_service.get_my_profile(user), user.id)


def resolve_role(user: CurrentUser, role_id: str | None) -> str:
    """The requested role, else the learner's saved target role; the learner always chooses."""
    if role_id:
        return role_id
    saved = repository.get_plan(user.id)
    if saved is None:
        raise AppError(
            "Choose a target role first: compare your matches and save a plan.",
            status_code=409,
            code="role_required",
        )
    return saved.role_id


def _learner(profile: Profile, user_id: str) -> engine.Learner:
    return engine.Learner(
        skill_levels=combined_levels(user_id, {s.skill_id: s.level for s in profile.skills}),
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
        for src in snapshot.all_sources():
            sources.setdefault(src.name, src)
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
    trend: trend_port.TrendView | None = None,
    catalogue: Sequence[Course] | None = None,
    snapshot_date: date | None = None,
) -> Pathway:
    """Plan towards `role_id` on the given trend view (default: the latest, or `snapshot_date`
    to replay an older M1 snapshot)."""
    reqs = data.requirements(role_id)
    labels = data.role_labels()
    if role_id not in labels or not reqs:
        raise NotFoundError(f"No pathway for role {role_id}")
    trend = trend or trend_port.current(scenario, snapshot_date)
    if trend is None and snapshot_date is not None:
        raise NotFoundError(f"No trend snapshot for {snapshot_date.isoformat()}")
    snapshot = trend.snapshot if trend else None
    growth = trend.growth if trend else {}
    plan = engine.build(
        reqs,
        learner,
        scenario,
        catalogue if catalogue is not None else data.catalogue(),
        data.prerequisites(),
        growth,
        data.skill_labels(),
        _sdg_by_skill([r.skill_id for r in reqs]),
        scenario_weighted=trend.scenario_weighted if trend else False,
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
        warnings=plan.warnings + _trend_warnings(trend, [r.skill_id for r in reqs]),
        snapshot_version=snapshot.version if snapshot else "",
    )


def _trend_warnings(trend: trend_port.TrendView | None, skill_ids: list[str]) -> list[str]:
    if trend is None:
        return ["No trend snapshot is available; skills are ordered by gap and importance only."]
    missing = trend.uncovered(skill_ids)
    if not missing:
        return []
    names = data.skill_labels()
    listed = ", ".join(names.get(s, s) for s in missing)
    return [
        f"The trend snapshot ({trend.snapshot.version}) has no signal for {listed}; "
        "they are treated as neutral demand, not rising or declining."
    ]


def get_pathway(
    user: CurrentUser, role_id: str, scenario: ScenarioId, snapshot_date: date | None = None
) -> Pathway:
    profile = profile_service.get_my_profile(user)
    plan = build_pathway(_learner(profile, user.id), role_id, scenario, snapshot_date=snapshot_date)
    # Attached after building, so the segment can only change guidance text, never the plan.
    return plan.model_copy(update={"segment": profile.segment})


# --- comparing roles before choosing ----------------------------------------------------

DIRECTION_BAND = 0.05  # same thresholds as M1's direction_<scenario> labels


def role_trend(
    reqs: Sequence[data.Requirement], trend: trend_port.TrendView | None
) -> tuple[float | None, float]:
    """Importance-weighted trend signal of a role's skills and the share of weight covered."""
    total = sum(r.importance for r in reqs)
    if not trend or total == 0:
        return None, 0.0
    covered = [r for r in reqs if r.skill_id in trend.growth]
    weight = sum(r.importance for r in covered)
    if weight == 0:
        return None, 0.0
    signal = sum(r.importance * trend.growth[r.skill_id] for r in covered) / weight
    return round(signal, 4), round(weight / total, 3)


def _direction(signal: float | None) -> str:
    if signal is None:
        return "unknown"
    if signal > DIRECTION_BAND:
        return "rising"
    if signal < -DIRECTION_BAND:
        return "declining"
    return "stable"


def compare_roles(
    user: CurrentUser,
    role_ids: Sequence[str],
    scenario: ScenarioId,
    snapshot_date: date | None = None,
) -> RoleComparison:
    """What each candidate role would take for this learner, side by side, before they choose."""
    learner = learner_for(user)
    trend = trend_port.current(scenario, snapshot_date)
    if trend is None and snapshot_date is not None:
        raise NotFoundError(f"No trend snapshot for {snapshot_date.isoformat()}")
    saved = repository.get_plan(user.id)
    known = data.target_role_ids()
    chosen = [r for r in dict.fromkeys(role_ids) if r in known] if role_ids else known
    options: list[RoleOption] = []
    plans: list[Pathway] = []
    for role_id in chosen:
        plan = build_pathway(learner, role_id, scenario, trend=trend)
        plans.append(plan)
        signal, coverage = role_trend(data.requirements(role_id), trend)
        options.append(
            RoleOption(
                role_id=role_id,
                role_label=plan.role_label,
                total_weeks=plan.total_weeks,
                total_hours=plan.total_hours,
                out_of_pocket_myr=plan.out_of_pocket_myr,
                within_budget=plan.within_budget,
                skills_to_close=sum(1 for g in plan.gaps if g.status != "have"),
                unmet_skills=len(plan.unmet),
                trend_signal=signal,
                trend_direction=_direction(signal),  # type: ignore[arg-type]
                trend_coverage=coverage,
                sdg_targets=[link.target for link in sdg_repository.role_links(role_id)],
                is_saved_choice=bool(saved and saved.role_id == role_id),
            )
        )
    snapshot = trend.snapshot if trend else None
    meta = _meta([step for p in plans for step in p.steps], snapshot, scenario)
    return RoleComparison(
        options=options,
        saved_role_id=saved.role_id if saved else None,
        snapshot_version=snapshot.version if snapshot else "",
        available_snapshots=list(trend.available_dates) if trend else [],
        meta=meta,
    )


def skills_gap(levels: Mapping[str, int], role_id: str) -> dict[str, list[str]]:
    """have / partial / missing skill ids for a role, using each skill's required level.

    The one gap rule for the app: F4 matching and the F7 heatmap should call this instead of
    their own thresholds, so a skill never shows as "missing" on one page and "partial" on another.
    """
    out: dict[str, list[str]] = {"have": [], "partial": [], "missing": []}
    for gap in engine.compute_gaps(data.requirements(role_id), levels, data.skill_labels()):
        out[gap.status].append(gap.skill_id)
    return out


@dataclass(frozen=True)
class CatalogueFilter:
    skill: str | None = None
    format: str | None = None
    audience: str | None = None  # "individual" also matches "both", likewise "corporate"
    provider_type: str | None = None
    hrd_claimable: bool | None = None
    max_cost_myr: float | None = None


def filter_courses(courses: Sequence[Course], f: CatalogueFilter) -> list[Course]:
    out = []
    for c in courses:
        if f.skill and f.skill not in c.skill_ids:
            continue
        if f.format and c.format != f.format:
            continue
        if f.audience and c.audience not in (f.audience, "both"):
            continue
        if f.provider_type and c.provider_type != f.provider_type:
            continue
        if f.hrd_claimable is not None and c.hrd_claimable != f.hrd_claimable:
            continue
        if f.max_cost_myr is not None and c.cost_myr > f.max_cost_myr:
            continue
        out.append(c)
    # Cheapest first, then shortest: the same preference the pathway engine uses.
    return sorted(out, key=lambda c: (c.cost_myr, c.hours, c.id))


def catalogue(f: CatalogueFilter | None = None) -> CatalogueResponse:
    courses = filter_courses(data.catalogue(), f or CatalogueFilter())
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
    latest_view = trend_port.current(saved.scenario if saved else "moderate")
    latest = latest_view.snapshot if latest_view else None
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
    # Any difference is proposed, never applied silently: new trend data, or a changed
    # profile (e.g. a skill confirmed at a higher level since the plan was saved).
    needs = bool(changes)
    if needs and newer and latest:
        message = (
            f"New trend data ({latest.source.name}, {latest.source.retrieved_at}) changes "
            f"{len(changes)} part(s) of your plan. Review and accept, or keep your current plan."
        )
    elif needs:
        message = (
            f"Your profile changed since you saved this plan; {len(changes)} part(s) would "
            "change. Review and accept, or keep your current plan."
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
    """The plan progress is tracked against: the saved plan for this role and scenario, else
    a fresh one. The same rule serves GET and POST, and the response carries the plan, so the
    page always shows exactly the courses the API accepts."""
    saved = repository.get_plan(user.id)
    if saved and saved.role_id == role_id and saved.scenario == scenario:
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


# Evidence that lets completed learning raise a skill level for matching (H08, decided
# 2026-10-22): a reviewer's confirmation, or a certificate link that opens on the provider's
# own verification page. Self-ticked courses show progress but do not change matches.
EARNED_EVIDENCE = frozenset({"org_confirmed", "certificate_link"})


def earned_levels(
    courses: Mapping[str, Course],
    statuses: Mapping[str, str],
    evidence: Mapping[str, CompletionEvidence],
) -> dict[str, int]:
    """Skill -> highest level reached by completed, evidenced courses (pure)."""
    out: dict[str, int] = {}
    for cid, status in statuses.items():
        course = courses.get(cid)
        if status != "completed" or course is None:
            continue
        if verification.evidence_strength(evidence.get(cid)) not in EARNED_EVIDENCE:
            continue
        for sid in course.skill_ids:
            out[sid] = max(out.get(sid, 0), course.level)
    return out


def evidenced_levels(user_id: str) -> dict[str, int]:
    """Accepted learning across every target, using the course facts saved with progress.

    Changing the saved target or retiring a catalogue course must not erase credit. Evidence
    is read afresh so undoing a completion or rejecting its proof still removes that credit.
    """
    by_role: dict[str, dict[str, str]] = {}
    for _uid, role_id, course_id, status in repository.progress_of([user_id]):
        by_role.setdefault(role_id, {})[course_id] = status
    out: dict[str, int] = {}
    for role_id, statuses in by_role.items():
        levels = earned_levels(
            repository.course_facts(user_id, role_id),
            statuses,
            repository.evidence(user_id, role_id),
        )
        for sid, level in levels.items():
            out[sid] = max(out.get(sid, 0), level)
    return out


def combined_levels(user_id: str, intake: Mapping[str, int]) -> dict[str, int]:
    """One effective skill input for matching, individual pathways and team gaps."""
    out = dict(intake)
    for sid, level in evidenced_levels(user_id).items():
        out[sid] = max(out.get(sid, 0), level)
    return out


def _plan_courses(plan: Pathway) -> dict[str, Course]:
    """Course facts as saved in the plan. Progress uses these, never the live catalogue, so a
    course retired later keeps the credit a learner already earned with it."""
    out: dict[str, Course] = {}
    for step in plan.steps:
        for c in step.courses:
            out.setdefault(c.id, c)
    return out


def get_progress(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Progress:
    plan = _plan_for_progress(user, role_id, scenario)
    raw = repository.course_status(user.id, role_id)
    evidence = repository.evidence(user.id, role_id)
    statuses = verification.effective_statuses(raw, evidence)
    courses = _plan_courses(plan)
    levels = {cid: {s: c.level for s in c.skill_ids} for cid, c in courses.items()}
    skills = progress.skill_progress(plan, statuses, levels)
    # Badges reflect current progress (undoing or a rejected completion removes what it
    # earned), keep the date each was first earned, and show the weakest evidence behind them.
    current = progress.earned_badges(plan, statuses, skills)
    first_earned = repository.record_badges(user.id, current, date.today())
    done = [cid for cid, st in statuses.items() if st == "completed" and cid in courses]
    labels = data.skill_labels()
    badges = []
    for badge_id in sorted(current):
        kind, skill_id, label = _badge_label(badge_id, labels)
        behind = [cid for cid in done if skill_id is None or skill_id in courses[cid].skill_ids]
        badges.append(
            Badge(
                id=badge_id,
                kind=kind,
                label=label,
                earned_at=first_earned[badge_id],
                evidence=verification.weakest(behind, evidence),  # type: ignore[arg-type]
                skill_id=skill_id,
            )
        )
    return Progress(
        role_id=role_id,
        course_status=raw,
        percent_complete=progress.percent_complete(plan, statuses),
        skills=skills,
        gap_closed=sum(1 for s in skills if s.closed),
        gap_total=len(skills),
        badges=badges,
        evidence=evidence,
        pathway=plan,
        meta=plan.meta,
    )


def _require_planned(plan: Pathway, role_id: str, course_id: str) -> Course:
    course = _plan_courses(plan).get(course_id)
    if course is None:
        raise AppError(
            f"Course {course_id} is not in your plan for {role_id}",
            status_code=422,
            code="unknown_course",
        )
    return course


def update_progress(user: CurrentUser, body: ProgressUpdate, scenario: ScenarioId) -> Progress:
    plan = _plan_for_progress(user, body.role_id, scenario)
    course = repository.course_facts(user.id, body.role_id).get(body.course_id) or _require_planned(
        plan, body.role_id, body.course_id
    )
    repository.set_course_status(user.id, body.role_id, body.course_id, body.status, course)
    if body.status == "completed":
        if body.course_id not in repository.evidence(user.id, body.role_id):
            repository.save_evidence(
                user.id,
                CompletionEvidence(
                    role_id=body.role_id,
                    course_id=body.course_id,
                    kind="self_reported",
                    submitted_at=datetime.now(UTC),
                ),
            )
    else:
        repository.delete_evidence(user.id, body.role_id, body.course_id)
    return get_progress(user, body.role_id, scenario)


def submit_evidence(
    user: CurrentUser,
    body: EvidenceSubmit,
    scenario: ScenarioId,
    check: verification.Probe | None = None,
) -> Progress:
    """Attach a certificate link; marks the course done. A new link resets any review."""
    check = check or verification.probe  # looked up per call, not frozen at import
    plan = _plan_for_progress(user, body.role_id, scenario)
    course = repository.course_facts(user.id, body.role_id).get(body.course_id) or _require_planned(
        plan, body.role_id, body.course_id
    )
    now = datetime.now(UTC)
    repository.set_course_status(user.id, body.role_id, body.course_id, "completed", course)
    repository.save_evidence(
        user.id,
        CompletionEvidence(
            role_id=body.role_id,
            course_id=body.course_id,
            kind="certificate_link",
            url=body.url,
            link_status=verification.check_link(body.url, course, check),
            link_checked_at=now,
            submitted_at=now,
        ),
    )
    return get_progress(user, body.role_id, scenario)


# --- HR / career-advisor review -------------------------------------------------------------


def _reviewer_org(user: CurrentUser) -> str:
    if user.kind != "org_admin" or not user.org_id:
        raise AppError(
            "Only HR or career-centre staff can review completions",
            status_code=403,
            code="forbidden",
        )
    return user.org_id


def _course_facts(user_id: str, role_id: str) -> dict[str, Course]:
    saved = repository.get_plan(user_id)
    facts = _plan_courses(saved.pathway) if saved and saved.role_id == role_id else {}
    return {**data.course_index(), **facts, **repository.course_facts(user_id, role_id)}


def verification_queue(user: CurrentUser) -> VerificationQueue:
    org_id = _reviewer_org(user)
    members = {m.id: m.display_name for m in org_repository.list_members(org_id)}
    items: list[VerificationItem] = []
    for uid, role_id, course_id, status in repository.progress_of(list(members)):
        if status != "completed":
            continue
        course = _course_facts(uid, role_id).get(course_id)
        if course is None:
            continue
        items.append(
            VerificationItem(
                user_id=uid,
                display_name=members[uid],
                role_id=role_id,
                course=course,
                status=status,
                evidence=repository.evidence(uid, role_id).get(course_id),
            )
        )
    reviewed = {"org_confirmed", "org_rejected"}
    pending = sum(1 for i in items if not i.evidence or i.evidence.kind not in reviewed)
    # Unreviewed first, strongest automatic evidence first within them.
    items.sort(
        key=lambda i: (
            bool(i.evidence and i.evidence.kind in reviewed),
            -verification.RANK.get(verification.evidence_strength(i.evidence), 0),
            i.display_name,
        )
    )
    return VerificationQueue(org_id=org_id, pending=pending, items=items)


def review_completion(user: CurrentUser, body: ReviewDecision) -> VerificationItem:
    org_id = _reviewer_org(user)
    members = {m.id: m.display_name for m in org_repository.list_members(org_id)}
    if body.user_id not in members:
        raise AppError("Not a member of your organisation", status_code=403, code="forbidden")
    status = repository.course_status(body.user_id, body.role_id).get(body.course_id)
    if status != "completed":
        raise AppError("This course is not marked as completed", status_code=409, code="conflict")
    course = _course_facts(body.user_id, body.role_id).get(body.course_id)
    if course is None:
        raise NotFoundError(f"Unknown course {body.course_id}")
    previous = repository.evidence(body.user_id, body.role_id).get(body.course_id)
    changed = AppError(
        "The learner changed this proof after you opened it. Reload and review it again.",
        status_code=409,
        code="evidence_changed",
    )
    if (previous.submitted_at if previous else None) != body.submitted_at:
        raise changed
    now = datetime.now(UTC)
    ev = (previous or CompletionEvidence(
        role_id=body.role_id, course_id=body.course_id, kind="self_reported", submitted_at=now
    )).model_copy(
        update={
            "kind": "org_confirmed" if body.decision == "confirm" else "org_rejected",
            "reviewed_by": user.id,
            "reviewed_at": now,
            "review_note": body.note,
        }
    )  # fmt: skip
    # Checked again in the same write, so a submission arriving now cannot be confirmed unseen.
    if not repository.review_evidence(body.user_id, ev, body.submitted_at):
        raise changed
    return VerificationItem(
        user_id=body.user_id,
        display_name=members[body.user_id],
        role_id=body.role_id,
        course=course,
        status=status,
        evidence=ev,
    )


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
