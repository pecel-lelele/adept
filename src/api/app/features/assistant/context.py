"""What Adi knows when it answers: the person's own Adept data, or public figures for visitors.

Each piece is optional. A piece that fails to load (no profile yet, database hiccup) is left out
and never guessed. The same facts feed the model prompt and the deterministic guide, and every
role, skill, course, SDG target and page Adi may cite is collected in `Refs`.
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
    "/app/sdg": "SDG impact",
    "/app/join": "Join a team",
    "/org": "Team home",
    "/org/members": "Team members",
    "/org/radar": "Team radar",
    "/org/gaps": "Team skill gaps",
    "/org/plan": "Team plan",
    "/org/sdg": "Team SDG impact",
    "/org/verify": "Review completions",
    "/auth/signup": "Create a free account",
    "/about": "How Adept works and its sources",
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
    audience: str  # "visitor" | "learner" | "manager"
    lines: list[str] = field(default_factory=list)
    refs: Refs = field(default_factory=Refs)
    grounded_on: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    meta: RecommendationMeta | None = None

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


def _catalogue_refs(refs: Refs) -> None:
    from app.features.pathway import data as pathway_data

    refs.roles.update(pathway_data.role_labels())
    refs.skills.update(pathway_data.skill_labels())
    for course in _try("catalogue", pathway_data.catalogue) or []:
        refs.courses[course.id] = (course.title, course.url)


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
    ctx.facts["my_trends"] = {i.skill_id: getattr(i, f"direction_{scenario}") for i in mine}
    ctx.grounded_on.append("trend snapshot")
    ctx.meta = RecommendationMeta(
        sources=[{"name": s.name, "url": s.url, "retrieved_at": s.retrieved_at} for s in m.sources],
        snapshot_date=m.snapshot_date,
        scenario=scenario,
        is_estimate=True,
        observed_from=m.observed_from,
        observed_to=m.observed_to,
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
            top = matches.matches[:5]
            ctx.facts["matches"] = [
                {
                    "role_id": m.role_id,
                    "score": m.score,
                    "missing": [s.id for s in m.missing_skills],
                    "partial": [s.id for s in m.partial_skills],
                    "parts": {c.name: c.value for c in m.components},
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
            for b in badges:
                ctx.refs.sdg[b.target] = b.label
            if badges:
                ctx.lines.append(
                    f"SDG targets of [[role:{top[0].role_id}]]: "
                    + ", ".join(f"[[sdg:{b.target}]]" for b in badges)
                )
            ctx.grounded_on.append("your matches")

    plan = _try("plan", lambda: pathway_service.get_saved_plan(user))
    if plan is not None:
        p = plan.pathway
        ctx.facts["plan_role"] = plan.role_id
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
        progress = _try(
            "progress", lambda: pathway_service.get_progress(user, plan.role_id, scenario)
        )
        if progress is not None:
            done = [cid for cid, st in progress.course_status.items() if st == "completed"]
            ctx.facts["done"] = done
            badges = ", ".join(b.id for b in progress.badges) or "none"
            ctx.lines.append(
                f"PROGRESS: {_pct(progress.percent_complete)} of planned hours done; "
                f"{len(done)} courses completed; skill gaps closed {progress.gap_closed} of "
                f"{progress.gap_total}; badges: {badges}."
            )
        ctx.grounded_on.append("your plan")
    _trends(ctx, scenario, own)


def _manager(ctx: Context, user: CurrentUser, scenario: ScenarioId) -> None:
    from app.features.org import service as org_service

    org = _try("org", lambda: org_service.get_my_org(user))
    if org is None:
        ctx.lines.append("The manager has not finished setting up the organisation.")
        _trends(ctx, scenario, set())
        return
    members = _try("members", lambda: org_service.list_members(user))
    if members is not None:
        total = len(members.members)
        done = sum(1 for m in members.members if m.intake_status == "complete")
        ctx.facts["members"] = (total, done)
        ctx.lines.append(
            f"TEAM '{org.name}' ({org.type}): {total} members, {done} with a complete skill "
            "profile (only complete profiles count in gaps and plans)."
        )
    gaps = _try("gaps", lambda: org_service.get_gaps(user, scenario))
    if gaps is not None and gaps.role_gaps:
        ranked = sorted(gaps.role_gaps.items(), key=lambda kv: -kv[1])[:5]
        ctx.facts["role_gaps"] = ranked
        ctx.lines.append(
            "Average team gap per target role (share of required skill level missing): "
            + ", ".join(f"[[role:{r}]] {_pct(g)}" for r, g in ranked)
        )
    plan = _try("team plan", lambda: org_service.get_plan(user, scenario))
    if plan is not None:
        ctx.facts["team_plan_role"] = plan.target_role_id
        ctx.lines.append(
            f"TEAM PLAN toward [[role:{plan.target_role_id}]]: {len(plan.steps)} steps, about "
            f"{plan.total_weeks} weeks, assigned to {len(plan.assigned_member_ids)} members."
        )
        for step in plan.steps[:5]:
            ctx.lines.append(
                f"  Step {step.order}: [[skill:{step.skill_id}]]: "
                + "; ".join(f"[[course:{c.id}]]" for c in step.courses)
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


def build(user: CurrentUser | None, scenario: ScenarioId) -> Context:
    if user is None:
        ctx = Context(audience="visitor")
    elif user.kind == "org_admin":
        ctx = Context(audience="manager")
    else:
        ctx = Context(audience="learner")
    ctx.lines.append(HOW_IT_WORKS)
    _catalogue_refs(ctx.refs)
    if user is None:
        _visitor(ctx, scenario)
    elif user.kind == "org_admin":
        _manager(ctx, user, scenario)
    else:
        _learner(ctx, user, scenario)
    return ctx
