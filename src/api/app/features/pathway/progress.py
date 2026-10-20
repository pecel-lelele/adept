"""Progress and badges (F5), pure functions.

Completing a course raises the learner's level in the skills it teaches to the course's level
(KerjaCerdas proof-level idea: this is *self-reported* evidence, weaker than an assessment or
an employer's confirmation, and badges say so). Badges:

    skill:<id>         the skill reached the role's required level
    milestone:first    first course completed
    milestone:halfway  at least half of the planned hours completed
    milestone:complete every planned course completed
"""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts.pathway import CourseStatus, Pathway, SkillProgress


def planned_courses(plan: Pathway) -> dict[str, float]:
    """course id -> hours, each booked course once."""
    out: dict[str, float] = {}
    for step in plan.steps:
        for c in step.courses:
            out.setdefault(c.id, c.hours)
    return out


def skill_progress(
    plan: Pathway, statuses: Mapping[str, CourseStatus], course_levels: Mapping[str, dict[str, int]]
) -> list[SkillProgress]:
    """course_levels: course id -> {skill id: level the course brings you to}."""
    out: list[SkillProgress] = []
    for gap in plan.gaps:
        if gap.status == "have":
            continue
        level = gap.current_level
        for course_id, status in statuses.items():
            if status == "completed":
                level = max(level, course_levels.get(course_id, {}).get(gap.skill_id, 0))
        out.append(
            SkillProgress(
                skill_id=gap.skill_id,
                label=gap.label,
                start_level=gap.current_level,
                current_level=level,
                target_level=gap.required_level,
                closed=level >= gap.required_level,
            )
        )
    return out


def percent_complete(plan: Pathway, statuses: Mapping[str, CourseStatus]) -> float:
    hours = planned_courses(plan)
    total = sum(hours.values())
    if not total:
        return 0.0
    done = sum(h for cid, h in hours.items() if statuses.get(cid) == "completed")
    return round(done / total, 3)


def earned_badges(
    plan: Pathway, statuses: Mapping[str, CourseStatus], skills: list[SkillProgress]
) -> list[str]:
    planned = planned_courses(plan)
    completed = [cid for cid in planned if statuses.get(cid) == "completed"]
    ids = [f"skill:{s.skill_id}" for s in skills if s.closed and s.current_level > s.start_level]
    if completed:
        ids.append("milestone:first")
    if percent_complete(plan, statuses) >= 0.5:
        ids.append("milestone:halfway")
    if planned and len(completed) == len(planned):
        ids.append("milestone:complete")
    return ids
