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
    return sorted(changes, key=lambda c: (c.kind, c.skill_id))
