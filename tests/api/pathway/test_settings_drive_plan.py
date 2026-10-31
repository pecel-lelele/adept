"""Onboarding settings visibly change the plan (production engine and re-plan diff)."""

from app.contracts.pathway import Pathway
from app.features.pathway import data, engine, replan, service

LABELS = data.skill_labels()


def _risk_plan(style: str, budget: float) -> engine.Plan:
    """risk-compliance level 2 has a live-online course (RM 490) and a free self-paced one."""
    return engine.build(
        [data.Requirement("risk-compliance", 2, 1)],
        engine.Learner({}, 5, budget, False, style),
        "moderate",
        data.catalogue(),
        {},
        {},
        LABELS,
    )


def _formats(plan: engine.Plan) -> set[str]:
    return {c.format for step in plan.steps for c in step.courses}


def test_classroom_style_prefers_taught_courses_within_budget() -> None:
    assert _formats(_risk_plan("classroom", 1000)) == {"live_online"}
    assert _formats(_risk_plan("video", 1000)) == {"self_paced"}
    assert _formats(_risk_plan("mixed", 1000)) == {"self_paced"}  # cheapest wins


def test_learning_style_never_exceeds_the_budget() -> None:
    plan = _risk_plan("classroom", 0)
    assert _formats(plan) == {"self_paced"}
    assert plan.out_of_pocket_myr == 0


def test_hours_per_week_change_the_schedule() -> None:
    def weeks(hours: float) -> int:
        learner = engine.Learner({"python": 1}, hours, 0, False)
        return service.build_pathway(learner, "cloud-solutions-architect", "moderate").total_weeks

    assert weeks(2) > weeks(5) > weeks(10)


def test_replan_proposes_schedule_and_cost_changes() -> None:
    def plan(hours: float, budget: float) -> Pathway:
        learner = engine.Learner({"python": 1}, hours, budget, False)
        return service.build_pathway(learner, "cloud-solutions-architect", "moderate")

    kinds = {c.kind for c in replan.diff_plans(plan(5, 0), plan(10, 0))}
    assert "schedule_changed" in kinds
    kinds = {c.kind for c in replan.diff_plans(plan(5, 0), plan(5, 500))}
    assert "cost_changed" in kinds
    assert replan.diff_plans(plan(5, 0), plan(5, 0)) == []
