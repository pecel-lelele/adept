"""Unit tests for the pure pathway engine (no API, no seed files)."""

from datetime import date

import pytest

from app.contracts.common import ScenarioId
from app.contracts.pathway import Course
from app.features.pathway import engine
from app.features.pathway.data import Requirement

D = date(2026, 10, 20)


def course(
    cid: str,
    skill: str,
    level: int,
    hours: float,
    cost: float = 0,
    hrd: bool = False,
    extra: tuple[str, ...] = (),
) -> Course:
    return Course(
        id=cid,
        title=cid,
        provider="P",
        url=f"https://x/{cid}",
        hours=hours,
        cost_myr=cost,
        hrd_claimable=hrd,
        verified_at=D,
        skill_ids=[skill, *extra],
        level=level,
    )


CATALOGUE = [
    course("sql-1", "sql", 2, 4),
    course("sql-2", "sql", 3, 6),
    course("viz-1", "viz", 3, 5),
    course("py-paid", "py", 3, 10, cost=900, hrd=True),
    course("py-free", "py", 3, 12),
]
LABELS = {"sql": "SQL", "viz": "Visualisation", "py": "Python", "x": "X"}


def learner(
    levels: dict[str, int] | None = None, hours: float = 5, budget: float = 0, hrd: bool = False
) -> engine.Learner:
    return engine.Learner(levels or {}, hours, budget, hrd)


def build(
    reqs: list[Requirement],
    who: engine.Learner,
    prereqs: dict[str, dict[str, str]] | None = None,
    growth: dict[str, float] | None = None,
    scenario: ScenarioId = "moderate",
    catalogue: list[Course] | None = None,
) -> engine.Plan:
    return engine.build(
        reqs, who, scenario, catalogue or CATALOGUE, prereqs or {}, growth or {}, LABELS
    )


def test_gap_statuses() -> None:
    reqs = [Requirement("sql", 3, 1), Requirement("py", 2, 1), Requirement("viz", 2, 1)]
    gaps = engine.compute_gaps(reqs, {"sql": 3, "py": 1}, LABELS)
    assert [g.status for g in gaps] == ["have", "partial", "missing"]


def test_skills_already_held_get_no_step() -> None:
    plan = build([Requirement("sql", 3, 1), Requirement("viz", 3, 1)], learner({"sql": 3}))
    assert [s.skill_id for s in plan.steps] == ["viz"]


def test_courses_climb_levels_in_order_and_stop_at_target() -> None:
    plan = build([Requirement("sql", 3, 1)], learner())
    assert [c.id for c in plan.steps[0].courses] == ["sql-1", "sql-2"]
    plan = build([Requirement("sql", 2, 1)], learner())
    assert [c.id for c in plan.steps[0].courses] == ["sql-1"]


def test_prerequisites_come_first_even_with_lower_priority() -> None:
    reqs = [Requirement("viz", 3, 1.0), Requirement("sql", 3, 0.1)]
    plan = build(reqs, learner(), prereqs={"viz": {"sql": "needs data"}})
    assert [s.skill_id for s in plan.steps] == ["sql", "viz"]
    assert plan.steps[1].prerequisites == ["sql"]


def test_prerequisite_inherits_the_urgency_of_what_it_unlocks() -> None:
    reqs = [Requirement("viz", 3, 1.0), Requirement("sql", 3, 0.1), Requirement("py", 3, 0.5)]
    plan = build(reqs, learner(), prereqs={"viz": {"sql": "needs data"}})
    assert [s.skill_id for s in plan.steps] == ["sql", "viz", "py"]


def test_cycles_are_rejected() -> None:
    with pytest.raises(engine.CycleError):
        engine.order_skills(["a", "b"], {"a": {"b": ""}, "b": {"a": ""}}, {})


def test_fast_scenario_boosts_rising_skills() -> None:
    reqs = [Requirement("sql", 3, 1.0), Requirement("py", 3, 0.9)]
    growth = {"py": 0.3}
    moderate = build(reqs, learner(budget=0), growth=growth, scenario="moderate")
    fast = build(reqs, learner(budget=0), growth=growth, scenario="fast")
    assert fast.steps[[s.skill_id for s in fast.steps].index("py")].priority > max(
        s.priority for s in moderate.steps if s.skill_id == "py"
    )
    assert [s.skill_id for s in fast.steps][0] == "py"


def test_free_course_preferred_when_not_hrd_eligible() -> None:
    plan = build([Requirement("py", 3, 1)], learner(budget=1000))
    assert [c.id for c in plan.steps[0].courses] == ["py-free"]
    assert plan.out_of_pocket_myr == 0


def test_hrd_claimable_course_costs_eligible_learner_nothing() -> None:
    plan = build([Requirement("py", 3, 1)], learner(budget=0, hrd=True))
    # Both cost RM0 to this learner; the shorter one wins.
    assert [c.id for c in plan.steps[0].courses] == ["py-paid"]
    assert plan.out_of_pocket_myr == 0 and plan.total_cost_myr == 900


def test_budget_is_respected() -> None:
    paid_only = [course("py-paid", "py", 3, 10, cost=900)]
    plan = build([Requirement("py", 3, 1)], learner(budget=100), catalogue=paid_only)
    assert plan.steps == []
    assert plan.unmet[0].reason == "over_budget"


def test_never_invents_a_course_for_an_uncovered_skill() -> None:
    plan = build([Requirement("x", 3, 1)], learner())
    assert plan.steps == [] and plan.unmet[0].reason == "no_catalogue_course"
    assert "will not invent" in plan.unmet[0].detail


def test_catalogue_ceiling_is_reported() -> None:
    plan = build([Requirement("sql", 4, 1)], learner())
    assert plan.steps[0].reaches_level == 3
    assert plan.unmet[0].reason == "catalogue_tops_out"


def test_a_multi_skill_course_is_booked_once() -> None:
    catalogue = [course("combo", "sql", 3, 10, extra=("viz",))]
    plan = build(
        [Requirement("sql", 3, 1.0), Requirement("viz", 3, 0.5)], learner(), catalogue=catalogue
    )
    assert plan.total_hours == 10
    assert plan.steps[1].est_hours == 0 and "already in step 1" in plan.steps[1].reason


def test_weeks_follow_hours_per_week() -> None:
    reqs = [Requirement("sql", 3, 1.0)]  # 4 h + 6 h
    assert build(reqs, learner(hours=5)).total_weeks == 2
    assert build(reqs, learner(hours=10)).total_weeks == 1
    plan = build(reqs, learner(hours=2))
    assert plan.total_weeks == 5 and plan.steps[0].week_end == 5


def test_zero_hours_falls_back_with_a_warning() -> None:
    plan = build([Requirement("sql", 3, 1)], learner(hours=0))
    assert plan.hours_per_week == engine.DEFAULT_HOURS_PER_WEEK and plan.warnings


@pytest.mark.parametrize(
    ("before", "after", "hpw", "expected"),
    [(0, 4, 5, (1, 1)), (4, 10, 5, (1, 2)), (10, 10, 5, (3, 3))],
)
def test_week_range(before: float, after: float, hpw: float, expected: tuple[int, int]) -> None:
    assert engine.week_range(before, after, hpw) == expected
