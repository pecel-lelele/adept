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

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.pathway import Pathway
from app.contracts.sdg import (
    EntitySdgLinks,
    GoalSummary,
    RegionListResponse,
    SdgAlignment,
    SdgContribution,
    SdgGoal,
    SdgGoalListResponse,
    SdgLink,
    SdgScope,
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
DEFAULT_ROLE_ID = "data-analyst"


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
                )
            )
        elif plan.within_budget:
            links.append(
                SdgLink(
                    target=targets["4.3"],
                    reason=f"The plan fits your RM {plan.budget_myr:g} budget.",
                    strength="enabling",
                    via="pathway",
                )
            )
    return links


def links_for_plan(plan: Pathway) -> list[SdgLink]:
    links = repository.role_links(plan.role_id)
    for step in plan.steps:
        links += repository.skill_links(step.skill_id)
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
    for person, plan in plans.items():
        mine = links_for_plan(plan)
        links += mine
        for link in mine:
            contributors.setdefault(link.target.goal, set()).add(person)
    unique = _dedupe(links)
    meta = _meta(scenario, is_estimate=True)
    plan_sources = [s for p in plans.values() for s in p.meta.sources]
    for src in plan_sources:
        if src.name not in {s.name for s in meta.sources}:
            meta.sources.append(src)
    role_ids = sorted({p.role_id for p in plans.values()})
    return SdgContribution(
        goals_summary=summarise(unique, contributors if scope != "person" else None),
        links=unique,
        meta=meta,
        scope=scope,
        scope_id=scope_id,
        role_ids=role_ids,
    )


def my_contribution(
    user: CurrentUser, role_id: str | None, scenario: ScenarioId
) -> SdgContribution:
    saved = pathway_service.get_saved_plan(user)
    chosen = role_id or (saved.role_id if saved else DEFAULT_ROLE_ID)
    plan = pathway_service.get_pathway(user, chosen, scenario)
    return contribution_for_plans({user.id: plan}, "person", user.id, scenario)


def org_contribution(org_id: str, scenario: ScenarioId) -> SdgContribution:
    plans = org_service.member_plans(org_id, scenario)
    return contribution_for_plans(plans, "organisation", org_id, scenario)


def region_contribution(state: str, scenario: ScenarioId) -> SdgContribution:
    org_ids = repository.orgs_in_state(state)
    if not org_ids:
        raise NotFoundError(f"No organisations in region {state}")
    plans: dict[str, Pathway] = {}
    for org_id in org_ids:
        plans.update(org_service.member_plans(org_id, scenario))
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
