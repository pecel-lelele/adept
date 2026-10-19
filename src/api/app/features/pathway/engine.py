"""Pathway engine (F5): pure functions, no I/O. `build` turns a skills gap into a plan.

    gap        role requirements minus the learner's levels → have / partial / missing
    priority   importance × gap share × trend multiplier (scenario-dependent)
    order      topological sort over prerequisite edges, ties broken by priority
    select     catalogue courses only, ascending level, cheapest out-of-pocket then shortest,
               within the remaining budget; a course covering several skills is booked once
    schedule   cumulative hours ÷ hours per week → contiguous week ranges

Identity never enters: `Learner` holds skill levels, hours, budget and HRD Corp eligibility
only, so the plan cannot depend on who the learner is (tests/api/pathway counterfactuals).
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.contracts.common import ScenarioId
from app.contracts.pathway import Course, PathwayStep, SkillGap, UnmetReason, UnmetSkill
from app.contracts.sdg import SdgTarget
from app.features.pathway.data import Requirement

# How strongly a skill's demand growth raises its priority, per scenario.
TREND_WEIGHT: dict[ScenarioId, float] = {"moderate": 1.0, "fast": 2.0}
GROWTH_CLIP = (-0.5, 1.0)
DEFAULT_HOURS_PER_WEEK = 5.0


class CycleError(ValueError):
    pass


@dataclass(frozen=True)
class Learner:
    skill_levels: Mapping[str, int]
    hours_per_week: float
    budget_myr: float
    hrd_eligible: bool


@dataclass
class Plan:
    steps: list[PathwayStep]
    gaps: list[SkillGap]
    unmet: list[UnmetSkill]
    total_hours: float
    total_weeks: int
    total_cost_myr: float
    out_of_pocket_myr: float
    hours_per_week: float
    warnings: list[str] = field(default_factory=list)


def compute_gaps(
    reqs: Sequence[Requirement], levels: Mapping[str, int], labels: Mapping[str, str]
) -> list[SkillGap]:
    gaps: list[SkillGap] = []
    for r in reqs:
        current = max(0, min(5, levels.get(r.skill_id, 0)))
        status = "have" if current >= r.required_level else "partial" if current > 0 else "missing"
        gaps.append(
            SkillGap(
                skill_id=r.skill_id,
                label=labels.get(r.skill_id, r.skill_id),
                current_level=current,
                required_level=r.required_level,
                importance=r.importance,
                status=status,
            )
        )
    return gaps


def trend_multiplier(growth: float, scenario: ScenarioId) -> float:
    lo, hi = GROWTH_CLIP
    return 1.0 + max(lo, min(hi, growth)) * TREND_WEIGHT[scenario]


def priority(gap: SkillGap, growth: float, scenario: ScenarioId) -> float:
    share = (gap.required_level - gap.current_level) / gap.required_level
    return round(gap.importance * share * trend_multiplier(growth, scenario), 4)


def order_skills(
    skill_ids: Sequence[str],
    prereqs: Mapping[str, Mapping[str, str]],
    prio: Mapping[str, float],
) -> list[str]:
    """Kahn's algorithm: prerequisites first, then highest priority, then skill id.

    A prerequisite inherits the highest priority among the skills it unlocks, so an urgent
    skill's foundation is scheduled before unrelated, less urgent skills.
    """
    nodes = set(skill_ids)
    indegree = {s: 0 for s in nodes}
    children: dict[str, list[str]] = {s: [] for s in nodes}
    for skill in nodes:
        for pre in prereqs.get(skill, {}):
            if pre in nodes:
                indegree[skill] += 1
                children[pre].append(skill)

    rank: dict[str, float] = {}

    def effective(skill: str, path: frozenset[str]) -> float:
        if skill in path:
            raise CycleError(f"prerequisite cycle through {skill}")
        if skill not in rank:
            below = [effective(c, path | {skill}) for c in children[skill]]
            rank[skill] = max([prio.get(skill, 0.0), *below])
        return rank[skill]

    for skill in nodes:
        effective(skill, frozenset())
    heap = [(-rank[s], -prio.get(s, 0.0), s) for s in nodes if indegree[s] == 0]
    heapq.heapify(heap)
    ordered: list[str] = []
    while heap:
        *_, skill = heapq.heappop(heap)
        ordered.append(skill)
        for child in children[skill]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(heap, (-rank[child], -prio.get(child, 0.0), child))
    if len(ordered) != len(nodes):
        raise CycleError(f"prerequisite cycle among {sorted(nodes - set(ordered))}")
    return ordered


def out_of_pocket(course: Course, hrd_eligible: bool) -> float:
    """What the learner pays: HRD Corp-claimable courses are employer-funded via the levy."""
    return 0.0 if course.hrd_claimable and hrd_eligible else course.cost_myr


@dataclass
class Selection:
    courses: list[Course]  # newly booked for this step
    covered_by_earlier: list[Course]  # already booked in an earlier step
    reaches_level: int
    alternatives: list[Course]
    unmet: UnmetReason | None


def select_courses(
    skill_id: str,
    current: int,
    required: int,
    catalogue: Sequence[Course],
    budget_left: float,
    hrd_eligible: bool,
    booked: set[str],
) -> Selection:
    # Subscriptions unlock courses rather than teach a skill: never booked as a step.
    candidates = [
        c
        for c in catalogue
        if skill_id in c.skill_ids and c.level > current and c.format != "subscription"
    ]
    by_cost = sorted(
        candidates, key=lambda c: (c.level, out_of_pocket(c, hrd_eligible), c.hours, c.id)
    )
    level = current
    new: list[Course] = []
    covered: list[Course] = []
    over_budget = False
    for target in sorted({c.level for c in candidates}):
        if level >= required:
            break
        if target <= level:
            continue
        options = [c for c in by_cost if c.level == target]
        already = next((c for c in options if c.id in booked), None)
        if already:
            covered.append(already)
            level = target
            continue
        affordable = [c for c in options if out_of_pocket(c, hrd_eligible) <= budget_left]
        if not affordable:
            over_budget = True
            continue
        pick = affordable[0]
        new.append(pick)
        budget_left -= out_of_pocket(pick, hrd_eligible)
        level = target
    chosen = {c.id for c in new + covered}
    alternatives = [c for c in by_cost if c.id not in chosen][:3]
    unmet: UnmetReason | None = None
    if level < required:
        if not candidates:
            unmet = "no_catalogue_course"
        elif over_budget:
            unmet = "over_budget"
        else:
            unmet = "catalogue_tops_out"
    return Selection(new, covered, level, alternatives, unmet)


def week_range(hours_before: float, hours_after: float, hours_per_week: float) -> tuple[int, int]:
    start = math.floor(hours_before / hours_per_week) + 1
    end = max(start, math.ceil(hours_after / hours_per_week))
    return start, end


_UNMET_DETAIL = {
    "no_catalogue_course": "No course in our catalogue teaches this skill yet; we will not "
    "invent one. Ask your employer or career centre, or learn on the job.",
    "over_budget": "Catalogue courses for this skill cost more than your remaining budget.",
    "catalogue_tops_out": "Catalogue courses stop at level {reached}; reaching level "
    "{required} needs practice on real work.",
}


def build(
    reqs: Sequence[Requirement],
    learner: Learner,
    scenario: ScenarioId,
    catalogue: Sequence[Course],
    prereqs: Mapping[str, Mapping[str, str]],
    growth: Mapping[str, float],
    labels: Mapping[str, str],
    sdg_targets: Mapping[str, list[SdgTarget]] | None = None,
) -> Plan:
    warnings: list[str] = []
    hpw = learner.hours_per_week
    if hpw <= 0:
        hpw = DEFAULT_HOURS_PER_WEEK
        warnings.append(
            f"No weekly study hours in your profile; the schedule assumes {hpw:g} h/week."
        )

    gaps = compute_gaps(reqs, learner.skill_levels, labels)
    open_gaps = {g.skill_id: g for g in gaps if g.status != "have"}
    prio = {s: priority(g, growth.get(s, 0.0), scenario) for s, g in open_gaps.items()}
    order = order_skills(list(open_gaps), prereqs, prio)

    budget_left = learner.budget_myr
    booked: dict[str, int] = {}  # course id -> step order that booked it
    steps: list[PathwayStep] = []
    unmet: list[UnmetSkill] = []
    hours = 0.0
    list_price = 0.0
    paid = 0.0
    for skill in order:
        gap = open_gaps[skill]
        sel = select_courses(
            skill,
            gap.current_level,
            gap.required_level,
            catalogue,
            budget_left,
            learner.hrd_eligible,
            set(booked),
        )
        if sel.unmet:
            reason = sel.unmet
            unmet.append(
                UnmetSkill(
                    skill_id=skill,
                    label=gap.label,
                    current_level=gap.current_level,
                    required_level=gap.required_level,
                    reason=reason,
                    detail=_UNMET_DETAIL[reason].format(
                        reached=sel.reaches_level, required=gap.required_level
                    ),
                )
            )
        if not sel.courses and not sel.covered_by_earlier:
            continue
        order_no = len(steps) + 1
        step_hours = sum(c.hours for c in sel.courses)
        step_paid = sum(out_of_pocket(c, learner.hrd_eligible) for c in sel.courses)
        start, end = week_range(hours, hours + step_hours, hpw)
        if step_hours == 0 and steps:
            start = end = steps[-1].week_end
        hours += step_hours
        list_price += sum(c.cost_myr for c in sel.courses)
        paid += step_paid
        budget_left -= step_paid
        for c in sel.courses:
            booked[c.id] = order_no
        pre = [p for p in prereqs.get(skill, {}) if p in open_gaps]
        steps.append(
            PathwayStep(
                order=order_no,
                skill_id=skill,
                skill_label=gap.label,
                courses=sel.courses + sel.covered_by_earlier,
                est_hours=round(step_hours, 1),
                week_start=start,
                week_end=end,
                reason=_reason(gap, prio[skill], growth.get(skill, 0.0), scenario, sel, booked),
                current_level=gap.current_level,
                target_level=gap.required_level,
                reaches_level=sel.reaches_level,
                priority=prio[skill],
                prerequisites=pre,
                alternatives=sel.alternatives,
                out_of_pocket_myr=round(step_paid, 2),
                sdg_targets=list((sdg_targets or {}).get(skill, [])),
            )
        )
    total_weeks = math.ceil(hours / hpw) if hours else 0
    return Plan(
        steps=steps,
        gaps=gaps,
        unmet=unmet,
        total_hours=round(hours, 1),
        total_weeks=total_weeks,
        total_cost_myr=round(list_price, 2),
        out_of_pocket_myr=round(paid, 2),
        hours_per_week=hpw,
        warnings=warnings,
    )


def _reason(
    gap: SkillGap,
    prio: float,
    growth: float,
    scenario: ScenarioId,
    sel: Selection,
    booked: Mapping[str, int],
) -> str:
    parts = [
        f"You are at level {gap.current_level}; the role needs {gap.required_level}.",
        f"Priority {prio:.2f} = importance {gap.importance:g} x gap "
        f"{(gap.required_level - gap.current_level) / gap.required_level:.0%} x trend "
        f"{trend_multiplier(growth, scenario):.2f} ({scenario} scenario, growth {growth:+.0%}).",
    ]
    for c in sel.covered_by_earlier:
        parts.append(f"'{c.title}' is already in step {booked[c.id]}.")
    return " ".join(parts)
