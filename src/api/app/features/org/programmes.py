"""Employer learning programmes (F7): objective → roles → personalised routes → agreements.

Decisions stay with people: HR chooses the objective, roles, people, date and budgets; Adept
proposes one route per person from the catalogue through the F5 engine (no separate course
formula), shows what it costs and whether it fits the date, and HR sends it. Each person then
accepts, declines (when optional) or asks for a change. A programme assignment is stored on its
own and never replaces the person's personal saved plan.
"""

from __future__ import annotations

import hashlib
import math
import secrets
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from app.contracts.common import RecommendationMeta
from app.contracts.funding import FundingState
from app.contracts.pathway import Course, Pathway, PathwayStep, UnmetSkill
from app.contracts.programmes import (
    Agreement,
    AssignmentDecision,
    MemberRoute,
    MyProgrammes,
    Objective,
    ObjectiveOption,
    ProgrammeAssignment,
    ProgrammeBriefIn,
    ProgrammeList,
    ProgrammeMember,
    ProgrammeOptions,
    ProgrammePlan,
    ProgrammeRecord,
    ProgrammeSend,
    ProgrammeStatus,
    RoleAllocation,
    RoleReadiness,
    Route,
)
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.org import funding, funding_store, repository, service
from app.features.pathway import data, engine, trend_port
from app.features.pathway import service as pathways

# Which catalogue roles serve each business objective. HR confirms or changes the choice; the
# mapping only shortens the list, it never decides the company's priorities.
OBJECTIVE_ROLES: dict[Objective, tuple[str, ...]] = {
    "ai_adoption": (
        "ai-operations-specialist",
        "ai-product-manager",
        "responsible-ai-officer",
        "machine-learning-engineer",
    ),
    "process_automation": (
        "process-automation-analyst",
        "business-analyst",
        "smart-manufacturing-engineer",
    ),
    "data_driven": (
        "data-analyst",
        "data-engineer",
        "business-analyst",
        "people-analytics-specialist",
    ),
    "customer_experience": (
        "customer-success-specialist",
        "ux-designer",
        "hospitality-experience-manager",
        "digital-marketing-specialist",
    ),
    "cybersecurity": ("cybersecurity-analyst", "cloud-solutions-architect"),
    "sustainability_esg": (
        "esg-sustainability-analyst",
        "energy-manager",
        "solar-pv-engineer",
        "precision-agriculture-specialist",
    ),
    "compliance_risk": (
        "compliance-analytics-officer",
        "islamic-finance-analyst",
        "responsible-ai-officer",
    ),
    "smart_manufacturing": (
        "smart-manufacturing-engineer",
        "semiconductor-process-engineer",
        "supply-chain-analyst",
    ),
    "digital_health": ("health-informatics-specialist", "digital-health-nurse"),
    "people_learning": (
        "learning-experience-designer",
        "tvet-digital-skills-trainer",
        "people-analytics-specialist",
    ),
    "digital_marketing": ("digital-marketing-specialist", "customer-success-specialist"),
    # Filled at request time with the roles the team is already closest to.
    "redeploy_at_risk": (),
}

READY = 0.7  # share of required levels held to count as "ready" / advanced route
FOUNDATION = 0.3


def _today() -> date:
    return datetime.now(UTC).date()


def readiness(levels: dict[str, int], role_id: str) -> float:
    """Importance-weighted share of a role's required levels already held (same rule as the
    team target and the gap heatmap)."""
    reqs = data.requirements(role_id)
    total = sum(r.importance for r in reqs)
    if total <= 0:
        return 0.0
    held = sum(r.importance * min(1.0, levels.get(r.skill_id, 0) / r.required_level) for r in reqs)
    return round(held / total, 4)


def route_for(share: float) -> Route:
    if share >= READY:
        return "advanced"
    if share >= FOUNDATION:
        return "applied"
    return "foundation"


def options(user: CurrentUser) -> ProgrammeOptions:
    org_id = funding.manager_scope(user)
    team = service.member_learners(org_id)
    names = {m.id: m.display_name for m in repository.list_members(org_id)}
    labels = data.role_labels()
    skill_labels = data.skill_labels()
    roles = []
    for role_id in data.target_role_ids():
        shares = [readiness(dict(lr.skill_levels), role_id) for lr in team.values()]
        reqs = data.requirements(role_id)
        roles.append(
            RoleReadiness(
                role_id=role_id,
                label=labels.get(role_id, role_id),
                skills=[r.skill_id for r in reqs],
                skill_labels=[skill_labels.get(r.skill_id, r.skill_id) for r in reqs],
                team_readiness=round(sum(shares) / len(shares), 4) if shares else 0.0,
                ready_members=sum(1 for s in shares if s >= READY),
            )
        )
    known = set(data.target_role_ids())
    closest = [r.role_id for r in sorted(roles, key=lambda r: -r.team_readiness)][:4]
    objectives = [
        ObjectiveOption(
            id=obj,
            role_ids=[r for r in (ids or tuple(closest)) if r in known],
        )
        for obj, ids in OBJECTIVE_ROLES.items()
    ]
    return ProgrammeOptions(
        objectives=objectives,
        roles=roles,
        members=[ProgrammeMember(user_id=uid, display_name=names.get(uid, uid)) for uid in team],
        default_target_date=_today() + timedelta(weeks=12),
        meta=RecommendationMeta(
            sources=[data.taxonomy_source(), service.TEAM_DATA_SOURCE],
            snapshot_date=data.taxonomy_source().retrieved_at,
            scenario="moderate",
            is_estimate=True,
        ),
    )


def _catalogue(brief: ProgrammeBriefIn) -> list[Course]:
    """Catalogue rows the brief allows: per-course prices only (no subscriptions), and the
    certificate, HRD Corp and delivery-format restrictions HR set."""
    out = []
    for c in data.catalogue():
        if c.format == "subscription" or c.price_basis != "per_course":
            continue
        if brief.certificate_required and c.price_status != "listed":
            continue
        if brief.hrd_claimable_only and not c.hrd_claimable and c.cost_myr > 0:
            continue
        if c.format not in brief.formats:
            continue
        out.append(c)
    return out


def generate(user: CurrentUser, brief: ProgrammeBriefIn) -> ProgrammePlan:
    org_id = funding.manager_scope(user)
    team = service.member_learners(org_id)
    names = {m.id: m.display_name for m in repository.list_members(org_id)}
    member_ids = sorted(set(brief.member_ids))
    missing = [uid for uid in member_ids if uid not in team]
    if missing:
        raise AppError(
            "Choose members of your organisation who have completed their skill profile.",
            status_code=422,
            code="unknown_member",
        )
    known = set(data.target_role_ids())
    roles = {}
    for target in brief.roles:
        if target.role_id not in known:
            raise NotFoundError(f"Unknown target role {target.role_id}")
        roles[target.role_id] = target.headcount
    weeks_available = max(0, math.ceil((brief.target_date - _today()).days / 7))
    if weeks_available < 1:
        raise AppError("Choose a target date at least a week from today.", status_code=422)
    labels = data.role_labels()
    notes: list[str] = []

    # 1. Match people to the roles the company wants, closest first, within each headcount.
    shares = {
        (uid, rid): readiness(dict(team[uid].skill_levels), rid)
        for uid in member_ids
        for rid in roles
    }
    remaining = dict(roles)
    assigned: dict[str, str] = {}
    for uid, rid in sorted(shares, key=lambda key: (-shares[key], key)):
        if uid in assigned or remaining[rid] <= 0:
            continue
        assigned[uid] = rid
        remaining[rid] -= 1
    unassigned = [uid for uid in member_ids if uid not in assigned]
    notes.append(
        f"Matched {len(assigned)} of {len(member_ids)} people to {len(roles)} role(s) by the "
        "share of each role's required skill levels they already hold, within each headcount."
    )
    if unassigned:
        notes.append(
            f"{len(unassigned)} people were not assigned: every role's headcount was filled."
        )

    # 2. Build each person's route under the brief's time, budget and course restrictions.
    catalogue = _catalogue(brief)
    excluded = len(data.catalogue()) - len(catalogue)
    if excluded:
        notes.append(f"{excluded} catalogue courses were left out by the programme's restrictions.")
    trend = trend_port.current(brief.scenario)
    budget_left = brief.budget_total_myr
    routes: list[MemberRoute] = []
    order = sorted(assigned, key=lambda uid: (assigned[uid], shares[(uid, assigned[uid])], uid))
    for uid in order:
        rid = assigned[uid]
        cap = max(0.0, min(brief.budget_per_member_myr, budget_left))
        learner = replace(
            team[uid], hours_per_week=brief.hours_per_week, budget_myr=cap, hrd_eligible=False
        )
        plan = pathways.build_pathway(
            learner, rid, brief.scenario, trend=trend, catalogue=catalogue
        )
        budget_left -= plan.total_cost_myr
        share = shares[(uid, rid)]
        needed = round(plan.total_hours / weeks_available, 1) if plan.total_hours else 0.0
        routes.append(
            MemberRoute(
                user_id=uid,
                display_name=names.get(uid, uid),
                role_id=rid,
                role_label=labels.get(rid, rid),
                route=route_for(share),
                readiness=share,
                pathway=plan,
                weeks_needed=plan.total_weeks,
                weeks_available=weeks_available,
                on_track=plan.total_weeks <= weeks_available,
                hours_per_week_needed=needed,
                cost_myr=plan.total_cost_myr,
                budget_myr=round(cap, 2),
                open_gaps=len(plan.unmet),
            )
        )
    total = round(sum(r.cost_myr for r in routes), 2)
    if routes and min(r.budget_myr for r in routes) < brief.budget_per_member_myr:
        notes.append(
            "The programme ceiling ran out before everyone reached their individual limit; "
            "later people get free or cheaper courses."
        )
    late = [r for r in routes if not r.on_track]
    if late:
        notes.append(
            f"{len(late)} people need more than {brief.hours_per_week:g} h/week to finish by "
            f"{brief.target_date.isoformat()}; each route shows the weekly hours needed."
        )
    allocations = [
        RoleAllocation(
            role_id=rid,
            role_label=labels.get(rid, rid),
            headcount=count,
            assigned=count - remaining[rid],
            shortfall=remaining[rid],
        )
        for rid, count in roles.items()
    ]
    meta = (
        routes[0].pathway.meta
        if routes
        else pathways.build_pathway(
            engine.Learner({}, brief.hours_per_week, 0, False),
            next(iter(roles)),
            brief.scenario,
            trend=trend,
            catalogue=catalogue,
        ).meta
    )
    plan = ProgrammePlan(
        brief=brief,
        token="",
        routes=routes,
        allocations=allocations,
        unassigned_member_ids=unassigned,
        total_cost_myr=total,
        within_programme_budget=total <= brief.budget_total_myr,
        members_on_track=len(routes) - len(late),
        notes=notes,
        meta=meta,
    )
    plan.token = _token(plan)
    return plan


def _token(plan: ProgrammePlan) -> str:
    body = plan.model_copy(update={"token": ""}).model_dump_json(exclude={"meta"})
    return hashlib.sha256(body.encode()).hexdigest()


def send(user: CurrentUser, body: ProgrammeSend) -> ProgrammeStatus:
    org_id = funding.manager_scope(user)
    plan = generate(user, body.brief)
    if plan.token != body.token:
        raise AppError(
            "Member skills, the catalogue or prices changed. Generate the plan again.",
            status_code=409,
            code="stale_programme",
        )
    now = datetime.now(UTC)
    record = ProgrammeRecord(
        id=f"prg-{secrets.token_hex(6)}",
        brief=body.brief,
        sent_at=now,
        sent_by=user.id,
        total_cost_myr=plan.total_cost_myr,
    )
    assignments = [
        ProgrammeAssignment(
            user_id=r.user_id,
            pathway=r.pathway,
            agreement=Agreement(
                programme_id=record.id,
                title=body.brief.title,
                objectives=body.brief.objectives,
                role_id=r.role_id,
                role_label=r.role_label,
                route=r.route,
                readiness=r.readiness,
                mandatory=body.brief.mandatory,
                target_date=body.brief.target_date,
                hours_per_week=body.brief.hours_per_week,
                budget_myr=r.budget_myr,
                cost_myr=r.cost_myr,
                sent_at=now,
                sent_by=user.id,
            ),
        )
        for r in plan.routes
    ]

    def save(state):  # type: ignore[no-untyped-def]
        state.programmes.append(record)
        state.assignments.extend(assignments)

    funding_store.transact(org_id, funding.current_year(), save)
    return _status(record, assignments)


def _status(record: ProgrammeRecord, assignments: list[ProgrammeAssignment]) -> ProgrammeStatus:
    mine = [a for a in assignments if a.agreement.programme_id == record.id]
    return ProgrammeStatus(
        record=record,
        assignments=mine,
        accepted=sum(a.status == "accepted" for a in mine),
        pending=sum(a.status == "assigned" for a in mine),
        declined=sum(a.status == "declined" for a in mine),
        change_requested=sum(a.status == "change_requested" for a in mine),
    )


_PRIVATE_UNMET = {
    "no_catalogue_course": "No catalogue course teaches this skill yet.",
    "over_budget": "Catalogue courses for this skill cost more than the agreed budget.",
    "catalogue_tops_out": "Catalogue courses do not reach the required level; it needs practice "
    "on real work.",
    "blocked_prerequisite": "A prerequisite skill must be established first.",
}


def private_route(pathway: Pathway) -> Pathway:
    """The route as an employer may see it for a member who does not share skill levels.

    Built from an allowlist, so a field added to the pathway later stays private by default.
    Kept: the courses, schedule, costs, target levels and SDG links (the employer funds and
    plans them). Dropped or neutralised: anything computed from the member's private levels,
    i.e. gap statuses, current and reached levels, priorities, the step explanations ("You are
    at level ..."), unmet details and profile warnings.
    """
    steps = [
        PathwayStep(
            order=step.order,
            skill_id=step.skill_id,
            skill_label=step.skill_label,
            courses=step.courses,
            alternatives=step.alternatives,
            est_hours=step.est_hours,
            week_start=step.week_start,
            week_end=step.week_end,
            target_level=step.target_level,
            # What the courses themselves teach (catalogue facts), never the member's level.
            reaches_level=min(step.target_level, max((c.level for c in step.courses), default=0)),
            prerequisites=step.prerequisites,
            out_of_pocket_myr=step.out_of_pocket_myr,
            sdg_targets=step.sdg_targets,
            reason=f"Builds {step.skill_label or step.skill_id} toward level "
            f"{step.target_level} for this programme.",
        )
        for step in pathway.steps
    ]
    unmet = [
        UnmetSkill(
            skill_id=u.skill_id,
            label=u.label,
            current_level=0,
            required_level=u.required_level,
            reason=u.reason,
            detail=_PRIVATE_UNMET.get(u.reason, ""),
        )
        for u in pathway.unmet
    ]
    return pathway.model_copy(
        update={"steps": steps, "unmet": unmet, "gaps": [], "warnings": [], "segment": None}
    )


def list_programmes(user: CurrentUser) -> ProgrammeList:
    org_id = funding.manager_scope(user)
    state = funding_store.snapshot(org_id)
    shared_members = {m.id: m.skills_shared for m in service.repository.list_members(org_id)}

    def _sanitize(assignment: ProgrammeAssignment) -> ProgrammeAssignment:
        if shared_members.get(assignment.user_id, False):
            return assignment
        return assignment.model_copy(update={"pathway": private_route(assignment.pathway)})

    return ProgrammeList(
        programmes=[
            _status(r, [_sanitize(a) for a in state.assignments])
            for r in reversed(state.programmes)
        ]
    )


def my_programmes(user: CurrentUser) -> MyProgrammes:
    if not user.org_id or user.kind == "org_admin":
        return MyProgrammes(assignments=[])
    state = funding_store.snapshot(user.org_id)
    mine = [a for a in state.assignments if a.user_id == user.id]
    return MyProgrammes(assignments=list(reversed(mine)))


def decide(user: CurrentUser, programme_id: str, body: AssignmentDecision) -> ProgrammeAssignment:
    if not user.org_id or user.kind == "org_admin":
        raise NotFoundError("No programme assignment.")
    if body.decision == "request_change" and body.reason is None:
        raise AppError("Say what should change.", status_code=422, code="reason_required")
    refreshed: Pathway | None = None
    current = next(
        (a for a in my_programmes(user).assignments if a.agreement.programme_id == programme_id),
        None,
    )
    if current is None:
        raise NotFoundError("No programme assignment.")
    if body.decision == "decline" and current.agreement.mandatory:
        raise AppError(
            "This programme is required by your employer. Ask for a change instead.",
            status_code=409,
            code="mandatory",
        )
    if body.decision == "accept":
        # Accepting re-checks the route against today's catalogue, prices and skills, within
        # what the employer committed, instead of adopting a stale copy.
        # When sharing is off and no explicit consent is given, do not bypass the sharing flag
        # with private profile levels.
        member = next(
            (m for m in service.repository.list_members(user.org_id) if m.id == user.id),
            None,
        )
        sharing_on = bool(member and member.skills_shared)
        if not sharing_on and not body.consent:
            raise AppError(
                "Consent to share your refreshed programme route with managers is required to "
                "accept this agreement.",
                status_code=400,
                code="sharing_consent_required",
            )
        learner = (
            service.member_learners(user.org_id, only=user.id).get(user.id)
            if (sharing_on or body.consent)
            else None
        )
        effective_budget = current.agreement.budget_myr
        if learner is not None:
            snap = funding_store.snapshot(user.org_id)
            record = next(r for r in snap.programmes if r.id == programme_id)
            # Cap the individual budget to the remaining programme ceiling so the
            # rebuilt route cannot silently exceed the total the employer committed.
            already_accepted = sum(
                a.agreement.cost_myr
                for a in snap.assignments
                if a.agreement.programme_id == programme_id
                and a.status == "accepted"
                and a.user_id != user.id
            )
            ceiling_left = max(0.0, record.brief.budget_total_myr - already_accepted)
            effective_budget = min(current.agreement.budget_myr, ceiling_left)
            refreshed = pathways.build_pathway(
                replace(
                    learner,
                    hours_per_week=current.agreement.hours_per_week,
                    budget_myr=effective_budget,
                    hrd_eligible=False,
                ),
                current.agreement.role_id,
                record.brief.scenario,
                catalogue=_catalogue(record.brief),
            )

    def change(state: FundingState) -> ProgrammeAssignment:
        for i, a in enumerate(state.assignments):
            if a.user_id == user.id and a.agreement.programme_id == programme_id:
                update: dict[str, object] = {
                    "status": {
                        "accept": "accepted",
                        "decline": "declined",
                        "request_change": "change_requested",
                    }[body.decision],
                    "decided_at": datetime.now(UTC),
                    "change_reason": body.reason,
                    "note": body.note.strip(),
                }
                if refreshed is not None:
                    update["pathway"] = refreshed
                    update["agreement"] = a.agreement.model_copy(
                        update={
                            "cost_myr": refreshed.total_cost_myr,
                            "budget_myr": effective_budget,
                        }
                    )
                state.assignments[i] = a.model_copy(update=update)
                # Enforce programme budget ceiling atomically within the transaction.
                if body.decision == "accept":
                    rec = next((r for r in state.programmes if r.id == programme_id), None)
                    if rec is not None:
                        accepted_total = sum(
                            sa.agreement.cost_myr
                            for sa in state.assignments
                            if sa.agreement.programme_id == programme_id and sa.status == "accepted"
                        )
                        if round(accepted_total, 2) > round(rec.brief.budget_total_myr, 2):
                            raise AppError(
                                "Accepting this route would exceed the programme's "
                                "total budget. Ask your manager to regenerate the "
                                "programme.",
                                status_code=409,
                                code="ceiling_exceeded",
                            )
                return state.assignments[i]
        raise NotFoundError("No programme assignment.")

    return funding_store.transact(user.org_id, funding.current_year(), change)


def accepted_pathway(user: CurrentUser, role_id: str) -> Pathway | None:
    """The newest accepted work programme route for `role_id` (progress is tracked against it)."""
    for a in my_programmes(user).assignments:
        if a.status == "accepted" and a.agreement.role_id == role_id:
            return a.pathway
    return None
