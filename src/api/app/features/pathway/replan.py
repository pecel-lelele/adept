"""Re-planning (F5): what changed between a saved plan and the plan rebuilt on new trend data.

The rebuilt plan is only *proposed*; the learner accepts it or keeps the saved one.
"""

from __future__ import annotations

from app.contracts.pathway import Pathway, PlanChange


def diff_plans(old: Pathway, new: Pathway) -> list[PlanChange]:
    old_steps = {s.skill_id: s for s in old.steps}
    new_steps = {s.skill_id: s for s in new.steps}
    changes: list[PlanChange] = []
    for skill, step in new_steps.items():
        if skill not in old_steps:
            changes.append(
                PlanChange(kind="added", skill_id=skill, detail=f"New step {step.order}.")
            )
    for skill, step in old_steps.items():
        if skill not in new_steps:
            changes.append(
                PlanChange(kind="removed", skill_id=skill, detail=f"Was step {step.order}.")
            )
    for skill in old_steps.keys() & new_steps.keys():
        before, after = old_steps[skill], new_steps[skill]
        if before.order != after.order:
            changes.append(
                PlanChange(
                    kind="reordered",
                    skill_id=skill,
                    detail=f"Step {before.order} -> {after.order} (priority "
                    f"{before.priority:.2f} -> {after.priority:.2f}).",
                )
            )
        if [c.id for c in before.courses] != [c.id for c in after.courses]:
            changes.append(
                PlanChange(kind="courses_changed", skill_id=skill, detail="Different courses.")
            )
    # Profile settings change the whole plan, not one step: hours per week move the weeks,
    # budget and HRD Corp eligibility move what the learner pays.
    if (old.hours_per_week, old.total_weeks) != (new.hours_per_week, new.total_weeks):
        changes.append(
            PlanChange(
                kind="schedule_changed",
                skill_id="",
                detail=f"{old.total_weeks} weeks at {old.hours_per_week:g} h/week -> "
                f"{new.total_weeks} weeks at {new.hours_per_week:g} h/week.",
            )
        )
    if (old.budget_myr, old.out_of_pocket_myr, old.hrd_eligible) != (
        new.budget_myr,
        new.out_of_pocket_myr,
        new.hrd_eligible,
    ):
        changes.append(
            PlanChange(
                kind="cost_changed",
                skill_id="",
                detail=f"Budget RM{old.budget_myr:g} -> RM{new.budget_myr:g}; "
                f"estimated cost RM{old.out_of_pocket_myr:g} -> RM{new.out_of_pocket_myr:g}.",
            )
        )
    return sorted(changes, key=lambda c: (c.kind, c.skill_id))
