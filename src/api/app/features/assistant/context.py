"""What Adi knows when it answers: the person's own Adept data, or public figures for visitors.

Each piece is optional. A piece that fails to load (no profile yet, database hiccup) is left out
and never guessed. `facts` render the guide's server-authored answer blocks (the model only
chooses among those blocks); `lines` is a readable summary of the same data, not sent to any
model. Every role, skill, course, SDG target and page Adi may cite is collected in `Refs`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from app.contracts.common import RecommendationMeta, ScenarioId
from app.core.auth import CurrentUser

log = logging.getLogger(__name__)
T = TypeVar("T")

# Pages Adi may link to, and what each is for (also used to explain the app).
PAGES: dict[str, str] = {
    "/app": "Home",
    "/app/onboarding": "Skill profile intake",
    "/app/profile": "My skills",
    "/app/radar": "Future Skills Radar",
    "/app/matches": "Matched roles",
    "/app/pathway": "Learning plan",
    "/app/pathway/compare": "Compare roles",
    "/app/progress": "Progress and badges",
    "/app/courses": "Course catalogue",
    "/app/jobs": "Job openings",
    "/app/sdg": "SDG impact",
    "/app/join": "Join an organisation",
    "/work": "Organisation home",
    "/work/skills": "What I share",
    "/work/plan": "Programme plans",
    "/work/progress": "Programme progress",
    "/org": "Team home",
    "/org/members": "Team members",
    "/org/radar": "Team radar",
    "/org/gaps": "Team skill gaps",
    "/org/programmes": "Programmes",
    "/org/programmes/new": "New programme",
    "/org/plan": "Team plan",
    "/org/sdg": "Team SDG impact",
    "/org/verify": "Review completions",
    "/auth/signup": "Create a free account",
    "/about": "How Adept works and its sources",
    "/privacy": "Privacy notice",
}


@dataclass
class Refs:
    """Everything Adi may cite, with its official label (the model never writes labels)."""

    roles: dict[str, str] = field(default_factory=dict)
    skills: dict[str, str] = field(default_factory=dict)
    courses: dict[str, tuple[str, str]] = field(default_factory=dict)  # id -> (title, url)
    sdg: dict[str, str] = field(default_factory=dict)
    pages: dict[str, str] = field(default_factory=lambda: dict(PAGES))


@dataclass
class Context:
    # "visitor" | "learner" (personal workspace) | "employee" (organisation member) | "manager"
    audience: str
    workspace: str = "personal"  # "personal" or the organisation id
    org_name: str = ""
    lines: list[str] = field(default_factory=list)
    refs: Refs = field(default_factory=Refs)
    grounded_on: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    meta: RecommendationMeta | None = None
    plan_meta: RecommendationMeta | None = None
    matches_meta: RecommendationMeta | None = None

    def text(self) -> str:
        return "\n".join(self.lines)


def _try(label: str, fn: Callable[[], T]) -> T | None:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - a missing piece is skipped, never invented
        log.info("assistant context: %s unavailable (%s)", label, type(exc).__name__)
        return None


def _pct(value: float) -> str:
    return f"{round(value * 100)}%"


def _plain(text: str) -> str:
    """Manager-authored text (organisation names, programme titles) must never form a reference
    tag when templated into an answer, so reference brackets are removed."""
    while "[[" in text or "]]" in text:
        text = text.replace("[[", "").replace("]]", "")
    return text.strip("[]")


def _catalogue_refs(refs: Refs) -> None:
    from app.features.pathway import data as pathway_data

    refs.roles.update(pathway_data.role_labels())
    refs.skills.update(pathway_data.skill_labels())
    for course in _try("catalogue", pathway_data.catalogue) or []:
        refs.courses[course.id] = (course.title, course.url)
    from app.features.sdg import repository as sdg_repository

    for target_id, target in (_try("sdg targets", sdg_repository.targets) or {}).items():
        refs.sdg[target_id] = f"SDG {target_id}: {target.label}"


def _trends(ctx: Context, scenario: ScenarioId, own: set[str]) -> None:
    from app.features.trends import service as trends_service

    snap = _try("trends", lambda: trends_service.get_snapshot(None, scenario))
    if snap is None:
        return
    key = f"velocity_{scenario}"
    items = sorted(snap.items, key=lambda i: getattr(i, key), reverse=True)
    rising = [i for i in items if getattr(i, f"direction_{scenario}") == "rising"][:5]
    declining = [i for i in reversed(items) if getattr(i, f"direction_{scenario}") == "declining"][
        :3
    ]
    m = snap.meta
    period = (
        f", measuring {m.observed_from} to {m.observed_to}"
        if m.observed_from and m.observed_to
        else ""
    )
    sources = "; ".join(s.name for s in m.sources)
    ctx.lines.append(
        f"TREND SNAPSHOT {m.snapshot_date} ({scenario} AI pace{period}; sources: {sources}). "
        "Trend directions are estimates."
    )
    if rising:
        ctx.lines.append("Rising skills: " + ", ".join(f"[[skill:{i.skill_id}]]" for i in rising))
    if declining:
        ctx.lines.append(
            "Declining skills: " + ", ".join(f"[[skill:{i.skill_id}]]" for i in declining)
        )
    mine = [i for i in items if i.skill_id in own]
    if mine:
        ctx.lines.append(
            "The person's skills on the radar: "
            + ", ".join(
                f"[[skill:{i.skill_id}]] {getattr(i, f'direction_{scenario}')}" for i in mine
            )
        )
    ctx.facts["rising"] = [i.skill_id for i in rising]
    ctx.facts["declining"] = [i.skill_id for i in declining]
    ctx.facts["declining_roles"] = [
        signal.entity_id
        for signal in trends_service.signals_from_snapshot(snap, scenario)
        if signal.entity_type == "role" and signal.direction == "declining"
    ]
    ctx.facts["my_trends"] = {i.skill_id: getattr(i, f"direction_{scenario}") for i in mine}
    ctx.grounded_on.append("trend snapshot")
    ctx.meta = RecommendationMeta(
        sources=[{"name": s.name, "url": s.url, "retrieved_at": s.retrieved_at} for s in m.sources],
        snapshot_date=m.snapshot_date,
        scenario=scenario,
        is_estimate=True,
        observed_from=m.observed_from,
        observed_to=m.observed_to,
        served_from=m.served_from,
        is_fallback=m.is_fallback,
    )


def _learner(ctx: Context, user: CurrentUser, scenario: ScenarioId) -> None:
    from app.features.matching import service as matching_service
    from app.features.pathway import service as pathway_service
    from app.features.profile import service as profile_service
    from app.features.sdg import service as sdg_service

    has_profile = bool(_try("profile check", lambda: profile_service.has_profile(user.id)))
    ctx.facts["has_profile"] = has_profile
    own: set[str] = set()
    if has_profile:
        profile = _try("profile", lambda: profile_service.get_my_profile(user))
        if profile is not None:
            own = {s.skill_id for s in profile.skills}
            ctx.facts["skills"] = {s.skill_id: s.level for s in profile.skills}
            ctx.facts["hours_per_week"] = profile.hours_per_week
            skills = ", ".join(
                f"[[skill:{s.skill_id}]] level {s.level}/5"
                for s in sorted(profile.skills, key=lambda s: -s.level)[:15]
            )
            ctx.lines.append(
                f"PROFILE: stage {profile.segment}; {profile.hours_per_week} h/week to learn; "
                f"budget RM {profile.budget_myr:g}; HRD Corp eligible: "
                f"{'yes' if profile.hrd_eligible else 'no'}; interests: "
                f"{', '.join(profile.interests) or 'none given'}."
            )
            ctx.lines.append(f"Confirmed skills: {skills or 'none yet'}.")
            ctx.grounded_on.append("your profile")

        matches = _try("matches", lambda: matching_service.list_matches(user, scenario))
        if matches is not None and matches.matches:
            ctx.matches_meta = matches.meta
            top = matches.matches[:5]
            ctx.facts["matches"] = [
                {
                    "role_id": m.role_id,
                    "score": m.score,
                    "missing": [s.id for s in m.missing_skills],
                    "partial": [s.id for s in m.partial_skills],
                    "parts": {c.name: c.value for c in m.components},
                    "components": [c.model_dump() for c in m.components],
                    "improvements": [item.model_dump() for item in m.improvements],
                }
                for m in top
            ]
            ctx.lines.append("MATCHED ROLES (fit score is an estimate; parts in brackets):")
            for m in top:
                parts = ", ".join(f"{c.name} {_pct(c.value)}×{c.weight:g}" for c in m.components)
                gap = ", ".join(f"[[skill:{s.id}]]" for s in m.missing_skills) or "none"
                partial = ", ".join(f"[[skill:{s.id}]]" for s in m.partial_skills) or "none"
                ctx.lines.append(
                    f"- [[role:{m.role_id}]] fit {_pct(m.score)} ({parts}); missing: {gap}; "
                    f"below required level: {partial}"
                )
            badges = _try("sdg", lambda: sdg_service.role_badges(top[0].role_id)) or []
            ctx.facts["sdg_targets"] = [b.target for b in badges]
            if badges:
                ctx.lines.append(
                    f"SDG targets of [[role:{top[0].role_id}]]: "
                    + ", ".join(f"[[sdg:{b.target}]]" for b in badges)
                )
            ctx.grounded_on.append("your matches")

    plan = _try("plan", lambda: pathway_service.get_saved_plan(user))
    if plan is not None:
        p = plan.pathway
        ctx.plan_meta = getattr(p, "meta", None)
        ctx.facts["plan_role"] = plan.role_id
        ctx.facts["plan_sdg_targets"] = list(
            dict.fromkeys(
                link.target.target
                for link in (_try("plan SDG links", lambda: sdg_service.links_for_plan(p)) or [])
            )
        )
        ctx.facts["plan_totals"] = {
            "weeks": p.total_weeks,
            "hours_per_week": p.hours_per_week,
            "hours": p.total_hours,
            "out_of_pocket_myr": p.out_of_pocket_myr,
            "list_price_myr": p.total_cost_myr,
        }
        ctx.lines.append(
            f"SAVED PLAN for [[role:{plan.role_id}]]: {len(p.steps)} steps, about {p.total_weeks} "
            f"weeks at {p.hours_per_week:g} h/week, {p.total_hours:g} h total, out of pocket "
            f"RM {p.out_of_pocket_myr:g} (list price RM {p.total_cost_myr:g})."
        )
        for step in p.steps[:6]:
            courses = "; ".join(
                f"[[course:{c.id}]] {c.hours:g} h, RM {c.cost_myr:g}"
                + (", HRD Corp claimable" if c.hrd_claimable else "")
                for c in step.courses
            )
            ctx.lines.append(
                f"  Step {step.order}: [[skill:{step.skill_id}]] level {step.current_level}"
                f"→{step.target_level}, weeks {step.week_start}-{step.week_end}: {courses}"
            )
        ctx.facts["plan_steps"] = [
            {"skill": s.skill_id, "courses": [c.id for c in s.courses]} for s in p.steps
        ]
        ctx.facts["plan_gaps"] = sum(1 for g in getattr(p, "gaps", []) if g.status != "have")
        progress = _try(
            "progress", lambda: pathway_service.get_progress(user, plan.role_id, plan.scenario)
        )
        if progress is not None:
            from app.features.pathway.verification import effective_statuses

            statuses = effective_statuses(progress.course_status, progress.evidence)
            done = [cid for cid, st in statuses.items() if st == "completed"]
            ctx.facts["done"] = done
            ctx.facts["plan_progress"] = {
                "share": progress.percent_complete,
                "courses": len(done),
                "gap_closed": progress.gap_closed,
                "gap_total": progress.gap_total,
            }
            badges = ", ".join(b.id for b in progress.badges) or "none"
            ctx.lines.append(
                f"PROGRESS: {_pct(progress.percent_complete)} of planned hours done; "
                f"{len(done)} courses completed; skill gaps closed {progress.gap_closed} of "
                f"{progress.gap_total}; badges: {badges}."
            )
        ctx.grounded_on.append("your plan")
    _trends(ctx, scenario, own)


def add_scenario_comparison(ctx: Context, user: CurrentUser | None, scenario: ScenarioId) -> None:
    """Compare the same person's profile on both stored scenarios at one snapshot date."""
    if user is None or ctx.audience != "learner" or ctx.matches_meta is None:
        return
    from app.features.matching import service as matching_service

    other: ScenarioId = "fast" if scenario == "moderate" else "moderate"
    snapshot_date = ctx.matches_meta.snapshot_date
    original = _try(
        "original scenario", lambda: matching_service.list_matches(user, scenario, snapshot_date)
    )
    alternative = _try(
        "other scenario", lambda: matching_service.list_matches(user, other, snapshot_date)
    )
    if (
        original is None
        or alternative is None
        or original.meta.snapshot_date != snapshot_date
        or alternative.meta.snapshot_date != snapshot_date
    ):
        return
    after = {
        match.role_id: (rank, match.score)
        for rank, match in enumerate(alternative.matches, start=1)
    }
    rows = [
        {
            "role_id": match.role_id,
            "before": match.score,
            "after": after[match.role_id][1],
            "rank_before": rank,
            "rank_after": after[match.role_id][0],
        }
        for rank, match in enumerate(original.matches[:5], start=1)
        if match.role_id in after
    ]
    if rows:
        ctx.meta = original.meta
        ctx.facts["scenario_comparison"] = {"before": scenario, "after": other, "roles": rows}


def _org_name(ctx: Context, user: CurrentUser) -> bool:
    from app.features.org import service as org_service

    org = _try("org", lambda: org_service.get_my_org(user))
    if org is None:
        return False
    ctx.org_name = _plain(org.name)
    ctx.workspace = org.id
    return True


def _employee(ctx: Context, user: CurrentUser, scenario: ScenarioId) -> None:
    """A member in their organisation's workspace: only their own participation in it."""
    from app.features.org import programmes
    from app.features.org import service as org_service
    from app.features.pathway import service as pathway_service

    if not _org_name(ctx, user):
        ctx.lines.append("The organisation workspace could not be loaded.")
        return
    ctx.lines.append(
        f"WORKSPACE: organisation '{ctx.org_name}'. Answer only about the person's participation "
        "in its programmes. Their personal plans, matches and conversations are private and "
        "belong to the personal workspace."
    )
    spaces = _try("workspaces", lambda: org_service.workspaces(user))
    if spaces is not None:
        mine = next((w for w in spaces.workspaces if w.id == ctx.workspace), None)
        ctx.facts["skills_shared"] = bool(mine and mine.skills_shared)
    assignments = _try("programmes", lambda: programmes.my_programmes(user).assignments) or []
    pending = [a for a in assignments if a.status in ("assigned", "change_requested")]
    accepted = [a for a in assignments if a.status == "accepted"]
    ctx.facts["work_pending"] = [
        {"title": _plain(a.agreement.title), "role": a.agreement.role_id, "status": a.status}
        for a in pending
    ]
    for a in pending:
        ctx.lines.append(
            f"PROGRAMME AWAITING THE PERSON ({a.status}): '{_plain(a.agreement.title)}' toward "
            f"[[role:{a.agreement.role_id}]], {a.agreement.hours_per_week:g} h/week until "
            f"{a.agreement.target_date}."
        )
    if accepted:
        a = accepted[0]
        work = {
            "title": _plain(a.agreement.title),
            "role": a.agreement.role_id,
            "date": a.agreement.target_date.isoformat(),
            "hours": a.agreement.hours_per_week,
            "budget": a.agreement.budget_myr,
            "courses": [c.id for s in a.pathway.steps for c in s.courses],
        }
        ctx.plan_meta = a.pathway.meta
        progress = _try(
            "work progress",
            lambda: pathway_service.get_progress(user, a.agreement.role_id, scenario),
        )
        if progress is not None:
            from app.features.pathway.verification import effective_statuses

            statuses = effective_statuses(progress.course_status, progress.evidence)
            work["done"] = [cid for cid, st in statuses.items() if st == "completed"]
            work["share"] = progress.percent_complete
        ctx.facts["work_active"] = work
        ctx.lines.append(
            f"ACCEPTED PROGRAMME '{work['title']}' toward [[role:{a.agreement.role_id}]]: "
            f"{a.agreement.hours_per_week:g} h/week of paid learning time until "
            f"{a.agreement.target_date}; employer committed up to RM {a.agreement.budget_myr:g}."
        )
    ctx.grounded_on.append(f"your {ctx.org_name} programmes")
    _trends(ctx, scenario, set())


def _manager(ctx: Context, user: CurrentUser, scenario: ScenarioId) -> None:
    from app.features.org import programmes
    from app.features.org import service as org_service

    if not _org_name(ctx, user):
        ctx.lines.append("The manager has not finished setting up the organisation.")
        _trends(ctx, scenario, set())
        return
    members = _try("members", lambda: org_service.list_members(user))
    if members is not None:
        total = len(members.members)
        done = sum(1 for m in members.members if m.intake_status == "complete")
        shared = sum(
            1 for m in members.members if m.intake_status == "complete" and m.skills_shared
        )
        ctx.facts["members"] = (total, done)
        ctx.facts["members_shared"] = shared
        ctx.lines.append(
            f"TEAM '{ctx.org_name}': {total} members, {done} with a complete skill profile, "
            f"{shared} of them sharing their skill levels (only those count in gaps and "
            "programme matching)."
        )
    gaps = _try("gaps", lambda: org_service.get_gaps(user, scenario))
    if gaps is not None and gaps.role_gaps:
        ranked = sorted(gaps.role_gaps.items(), key=lambda kv: -kv[1])[:5]
        ctx.facts["role_gaps"] = ranked
        ctx.lines.append(
            "Average team gap per target role (share of required skill level missing): "
            + ", ".join(f"[[role:{r}]] {_pct(g)}" for r, g in ranked)
        )
    sent = _try("programmes", lambda: programmes.list_programmes(user).programmes)
    if sent is not None:
        ctx.facts["programmes"] = [
            {
                "title": _plain(p.record.brief.title),
                "accepted": p.accepted,
                "pending": p.pending,
                "declined": p.declined,
                "changes": p.change_requested,
            }
            for p in sent
        ]
        for p in sent[:5]:
            roles = ", ".join(f"[[role:{r.role_id}]]" for r in p.record.brief.roles)
            ctx.lines.append(
                f"PROGRAMME '{_plain(p.record.brief.title)}' ({roles}) due "
                f"{p.record.brief.target_date}: "
                f"{p.accepted} accepted, {p.pending} waiting, {p.change_requested} asked for "
                f"changes, {p.declined} declined."
            )
    ctx.grounded_on.append("your team")
    _trends(ctx, scenario, set())


def _visitor(ctx: Context, scenario: ScenarioId) -> None:
    from app.core import overview

    o = _try("overview", overview.get)
    if o is not None:
        ctx.lines.append(
            f"ADEPT TODAY: {o.skills_in_bank} skills in the skill bank, {o.skills_tracked} "
            f"tracked in the trend snapshot ({o.rising} rising, {o.declining} declining), "
            f"{o.roles} future roles ranked, {o.courses} courses from {o.providers} providers "
            f"({o.free_courses} free, {o.hrd_claimable_courses} HRD Corp claimable), "
            f"{o.sdg_goals_linked} UN goals linked."
        )
        ctx.lines.append(
            "Roles with the strongest outlook: "
            + ", ".join(f"[[role:{r.role_id}]]" for r in o.top_roles[:4])
        )
        ctx.grounded_on.append("Adept's public figures")
    _trends(ctx, scenario, set())


HOW_IT_WORKS = (
    "HOW ADEPT WORKS: 1) Tell us about yourself: upload a CV (PDF, Word or text, read in memory "
    "and never stored) or pick skills. 2) Future Skills Radar: which skills are rising or "
    "declining, from research-attention (arXiv cs.AI) and labour-market projections, dated and "
    "sourced. 3) Matched roles: fit score = skill overlap + trend outlook + interest fit, with "
    "the skills gap. 4) Learning plan: ordered courses from a verified catalogue with hours, cost "
    "and HRD Corp claimability, each step linked to UN SDG targets. Two AI-pace scenarios "
    "(moderate, fast). Predictions are estimates; people make the decisions; Adept never makes "
    "hiring decisions."
)


def audience_of(user: CurrentUser | None) -> str:
    if user is None:
        return "visitor"
    if user.kind == "org_admin":
        return "manager"
    return "employee" if user.workspace == "org" and user.org_id else "learner"


def build(user: CurrentUser | None, scenario: ScenarioId) -> Context:
    """Facts for the workspace the question was asked in, and nothing from other workspaces."""
    ctx = Context(audience=audience_of(user))
    ctx.lines.append(HOW_IT_WORKS)
    _catalogue_refs(ctx.refs)
    if user is None:
        _visitor(ctx, scenario)
    elif ctx.audience == "manager":
        _manager(ctx, user, scenario)
    elif ctx.audience == "employee":
        _employee(ctx, user, scenario)
    else:
        ctx.lines.append("WORKSPACE: personal. Plans and matches here are private to the person.")
        _learner(ctx, user, scenario)
    return ctx
