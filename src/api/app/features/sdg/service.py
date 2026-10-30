"""SDG logic (F6).

Mapping method: curated role → target and skill → target links (seed CSVs), each with a reason
and a strength, drafted by M3 and pending human review. Contributions are *computed from the
plan*, not decorative:

- person:        the chosen role's links + links of the skills the pathway builds + plan-level
                 links derived from plan facts (skills built → 4.4; cost barrier removed → 4.3)
- organisation:  the same over each member's part of the group plan; `contributors` counts
                 the people whose plan touches each goal
- region:        organisations in a Malaysian state, combined

`alignment` scores a role against chosen goals so F4 can weight ranking by SDG preference.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.pathway import Pathway
from app.contracts.sdg import (
    EntitySdgLinks,
    GoalSummary,
    RegionListResponse,
    SdgAlignment,
    SdgContribution,
    SdgEvidence,
    SdgGoal,
    SdgGoalListResponse,
    SdgLink,
    SdgScope,
    SdgTarget,
    TargetContribution,
)
from app.core.auth import CurrentUser
from app.core.errors import NotFoundError
from app.features.org import service as org_service
from app.features.pathway import service as pathway_service
from app.features.sdg import repository

# Domain focus goals for the Aiversecity Future-Ready Workforce domain.
FOCUS_GOALS: tuple[int, ...] = (4, 5, 8, 9, 10)
STRENGTH_WEIGHT = {"direct": 1.0, "enabling": 0.5}
# Strength-weighted sum at which a role counts as fully aligned with the chosen goals.
ALIGNMENT_CAP = 2.0


def _meta(scenario: ScenarioId = "moderate", is_estimate: bool = False) -> RecommendationMeta:
    un = repository.un_source()
    return RecommendationMeta(
        sources=[un, repository.mapping_source()],
        snapshot_date=un.retrieved_at,
        scenario=scenario,
        is_estimate=is_estimate,
    )


def goals() -> SdgGoalListResponse:
    targets = repository.targets()
    un = repository.un_source()
    out = [
        SdgGoal(
            goal=int(g["id"]),
            title=g["title"],
            short_title=g["short_title"],
            is_focus=int(g["id"]) in FOCUS_GOALS,
            targets=[t for t in targets.values() if t.goal == int(g["id"])],
            source=un.model_copy(update={"url": g["source_url"]}),
        )
        for g in repository.goals()
    ]
    return SdgGoalListResponse(goals=out, focus_goals=list(FOCUS_GOALS), meta=_meta())


def role_sdg(role_id: str) -> EntitySdgLinks:
    links = repository.role_links(role_id)
    if not links:
        raise NotFoundError(f"No SDG links for role {role_id}")
    return EntitySdgLinks(entity_type="role", entity_id=role_id, links=links, meta=_meta())


def skill_sdg(skill_id: str) -> EntitySdgLinks:
    links = repository.skill_links(skill_id)
    if not links:
        raise NotFoundError(f"No SDG links for skill {skill_id}")
    return EntitySdgLinks(entity_type="skill", entity_id=skill_id, links=links, meta=_meta())


# --- contributions -----------------------------------------------------------------


_META = "https://unstats.un.org/sdgs/metadata/files/Metadata-{}.pdf"


def _evidence(name: str, code: str, note: str) -> SdgEvidence:
    return SdgEvidence(
        source=Source(name=name, url=_META.format(code), retrieved_at=repository.EVIDENCE_CHECKED),
        note=note,
    )


EVIDENCE_4_4 = _evidence(
    "UN SDG indicator metadata 4.4.1 (custodian ITU, updated 2025-03-28)",
    "04-04-01",
    'Among the ICT skills 4.4.1 counts is "Doing an online course or accessing online learning '
    'material", alongside the skill types each step builds.',
)
EVIDENCE_4_3 = _evidence(
    "UN SDG indicator metadata 4.3.1 (updated 2024-07-29)",
    "04-03-01",
    "4.3.1 is the participation rate of youth and adults in formal and non-formal education "
    "and training in the previous 12 months; target 4.3 asks for affordable access to it.",
)


def plan_links(plan: Pathway) -> list[SdgLink]:
    """Links that follow from facts about the plan itself."""
    targets = repository.targets()
    built = [s.skill_label or s.skill_id for s in plan.steps]
    links: list[SdgLink] = []
    if built:
        links.append(
            SdgLink(
                target=targets["4.4"],
                reason=f"This plan builds {len(built)} skill(s) for employment: "
                f"{', '.join(built)}.",
                strength="direct",
                via="pathway",
                evidence=EVIDENCE_4_4,
            )
        )
        if plan.out_of_pocket_myr == 0:
            links.append(
                SdgLink(
                    target=targets["4.3"],
                    reason="Every course in this plan is free or HRD Corp-funded for you, so "
                    "cost is not a barrier to technical education.",
                    strength="direct",
                    via="pathway",
                    evidence=EVIDENCE_4_3,
                )
            )
        elif plan.within_budget:
            links.append(
                SdgLink(
                    target=targets["4.3"],
                    reason=f"The plan fits your RM {plan.budget_myr:g} budget.",
                    strength="enabling",
                    via="pathway",
                    evidence=EVIDENCE_4_3,
                )
            )
    return links


def links_for_plan(plan: Pathway) -> list[SdgLink]:
    links = repository.role_links(plan.role_id)
    skills = {step.skill_id for step in plan.steps} | {
        skill for step in plan.steps for course in step.courses for skill in course.skill_ids
    }
    for skill in sorted(skills):
        links += repository.skill_links(skill)
    return links + plan_links(plan)


def summarise(
    links: Sequence[SdgLink], contributors_by_goal: dict[int, set[str]] | None = None
) -> list[GoalSummary]:
    """All 17 goals, so goals a plan does *not* touch are visible too."""
    titles = repository.short_titles()
    out: list[GoalSummary] = []
    for goal in range(1, 18):
        mine = [link for link in links if link.target.goal == goal]
        out.append(
            GoalSummary(
                goal=goal,
                label=titles.get(goal, f"SDG {goal}"),
                link_count=len(mine),
                direct_count=sum(1 for link in mine if link.strength == "direct"),
                enabling_count=sum(1 for link in mine if link.strength == "enabling"),
                is_focus=goal in FOCUS_GOALS,
                contributors=len((contributors_by_goal or {}).get(goal, set())),
            )
        )
    return out


def _dedupe(links: Iterable[SdgLink]) -> list[SdgLink]:
    seen: dict[tuple[str, str, str], SdgLink] = {}
    for link in links:
        seen.setdefault((link.target.target, link.via, link.reason), link)
    return list(seen.values())


def contribution_for_plans(
    plans: dict[str, Pathway], scope: SdgScope, scope_id: str, scenario: ScenarioId
) -> SdgContribution:
    """plans: person id -> that person's plan (or their part of a group plan)."""
    links: list[SdgLink] = []
    contributors: dict[int, set[str]] = {}
    target_hours: dict[str, float] = {}
    goal_hours: dict[int, float] = {}
    total_hours = 0.0
    known = repository.targets()
    for person, plan in plans.items():
        mine = links_for_plan(plan)
        links += mine
        for link in mine:
            contributors.setdefault(link.target.goal, set()).add(person)
        for step in plan.steps:
            hours = step.est_hours
            total_hours += hours
            skills = {step.skill_id} | {
                skill for course in step.courses for skill in course.skill_ids
            }
            targets = {
                link.target.target for skill in skills for link in repository.skill_links(skill)
            }
            for target in targets:
                target_hours[target] = target_hours.get(target, 0) + hours
            for goal in {known[target].goal for target in targets}:
                goal_hours[goal] = goal_hours.get(goal, 0) + hours
    unique = _dedupe(links)
    meta = _meta(scenario, is_estimate=True)
    plan_sources = [s for p in plans.values() for s in p.meta.sources]
    for src in plan_sources:
        if src.name not in {s.name for s in meta.sources}:
            meta.sources.append(src)
    if plans:
        fallback = any(plan.meta.is_fallback for plan in plans.values())
        served_from = {plan.meta.served_from for plan in plans.values()}
        meta = meta.model_copy(
            update={
                "snapshot_date": min(plan.meta.snapshot_date for plan in plans.values()),
                "is_fallback": fallback,
                "served_from": "fixture"
                if "fixture" in served_from
                else "db"
                if served_from == {"db"}
                else None,
            }
        )
    role_ids = sorted({p.role_id for p in plans.values()})
    summaries = [
        goal.model_copy(
            update={
                "planned_hours": goal_hours.get(goal.goal, 0),
                "hours_share": min(1.0, goal_hours.get(goal.goal, 0) / total_hours)
                if total_hours
                else 0,
            }
        )
        for goal in summarise(unique, contributors if scope != "person" else None)
    ]
    return SdgContribution(
        goals_summary=summaries,
        links=unique,
        meta=meta,
        scope=scope,
        scope_id=scope_id,
        role_ids=role_ids,
        target_contributions=[
            TargetContribution(
                target=known[target], planned_hours=hours, hours_share=min(1.0, hours / total_hours)
            )
            for target, hours in sorted(target_hours.items(), key=lambda item: (-item[1], item[0]))
            if hours > 0 and total_hours > 0
        ],
    )


def my_contribution(
    user: CurrentUser, role_id: str | None, scenario: ScenarioId
) -> SdgContribution:
    saved = pathway_service.get_saved_plan(user)
    chosen = role_id or (saved.role_id if saved else None)
    if chosen is None:
        # No role chosen yet: show nothing rather than assume one for the learner.
        return contribution_for_plans({}, "person", user.id, scenario)
    plan = pathway_service.get_pathway(user, chosen, scenario)
    return contribution_for_plans({user.id: plan}, "person", user.id, scenario)


def role_badges(role_id: str) -> list[SdgTarget]:
    """SDG targets to show as badges on a role (F4 matches, F5 compare): the reviewed mapping in
    `role_sdg_map.csv`, never a hardcoded list. Empty when the role is not mapped yet."""
    return [link.target for link in repository.role_links(role_id)]


def org_contribution(
    org_id: str, scenario: ScenarioId, role_id: str | None = None
) -> SdgContribution:
    """Aggregate of every counted member's plan towards the selected (or default) role."""
    plans = org_service.member_plans(org_id, scenario, role_id)
    return contribution_for_plans(plans, "organisation", org_id, scenario)


def region_contribution(
    state: str, scenario: ScenarioId, role_id: str | None = None
) -> SdgContribution:
    org_ids = repository.orgs_in_state(state)
    if not org_ids:
        raise NotFoundError(f"No organisations in region {state}")
    plans: dict[str, Pathway] = {}
    for org_id in org_ids:
        plans.update(org_service.member_plans(org_id, scenario, role_id))
    return contribution_for_plans(plans, "region", state, scenario)


def regions() -> RegionListResponse:
    return RegionListResponse(regions=repository.states())


# --- alignment for SDG-weighted ranking (F4) ---------------------------------------------


def alignment(role_id: str, goal_ids: Sequence[int]) -> SdgAlignment:
    links = repository.role_links(role_id)
    if not links:
        raise NotFoundError(f"No SDG links for role {role_id}")
    chosen = sorted(set(goal_ids) or set(FOCUS_GOALS))
    hits = [link for link in links if link.target.goal in chosen]
    raw = sum(STRENGTH_WEIGHT[link.strength] for link in hits)
    score = round(min(1.0, raw / ALIGNMENT_CAP), 3)
    explanation = (
        f"{len(hits)} link(s) to goals {', '.join(map(str, chosen))}: "
        f"direct = 1.0, enabling = 0.5, sum {raw:g} / {ALIGNMENT_CAP:g} (capped at 1)."
    )
    return SdgAlignment(
        role_id=role_id,
        goals=chosen,
        score=score,
        explanation=explanation,
        links=hits,
        meta=_meta(),
    )
