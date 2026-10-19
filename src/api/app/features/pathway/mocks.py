"""Mock pathway. Courses are SYNTHETIC placeholders (example.org); F5 (M3) replaces them
with a manually verified catalogue of real, dated course URLs."""

from datetime import date

from app.contracts.pathway import Course, PathwayStep

VERIFIED = date(2026, 10, 20)

COURSES: dict[str, Course] = {
    "course-rpa-101": Course(id="course-rpa-101", title="Intro to Process Automation (sample)",
                             provider="Sample Provider", url="https://example.org/courses/rpa-101",
                             hours=12, cost_myr=0, hrd_claimable=False, verified_at=VERIFIED),
    "course-python-basics": Course(id="course-python-basics", title="Python Basics (sample)",
                                   provider="Sample Provider",
                                   url="https://example.org/courses/python-basics",
                                   hours=20, cost_myr=0, hrd_claimable=False, verified_at=VERIFIED),
    "course-sql-101": Course(id="course-sql-101", title="SQL for Analysts (sample)",
                             provider="Sample Training Centre",
                             url="https://example.org/courses/sql-101",
                             hours=15, cost_myr=350, hrd_claimable=True, verified_at=VERIFIED),
    "course-dataviz": Course(id="course-dataviz", title="Dashboards & Data Visualisation (sample)",
                             provider="Sample Training Centre",
                             url="https://example.org/courses/dataviz",
                             hours=10, cost_myr=250, hrd_claimable=True, verified_at=VERIFIED),
}  # fmt: skip

# role_id -> [(skill_id, course_ids, reason)]
PLANS: dict[str, list[tuple[str, list[str], str]]] = {
    "data-analyst": [
        ("sql", ["course-sql-101"], "Most data-analyst postings require SQL (mock reason)."),
        ("python", ["course-python-basics"], "Builds on SQL for automation (mock reason)."),
        ("data-visualisation", ["course-dataviz"], "Turns analysis into decisions (mock)."),
    ],
    "process-automation-analyst": [
        ("process-mapping", ["course-dataviz"], "Raise your level from 2 to 3 (mock reason)."),
        ("rpa", ["course-rpa-101"], "Core skill for the role (mock reason)."),
        ("python", ["course-python-basics"], "Needed for custom automations (mock reason)."),
    ],
}


def steps(role_id: str, hours_per_week: int) -> list[PathwayStep]:
    """Mock schedule: consecutive weeks from course hours. Real ordering is F5 logic."""
    result: list[PathwayStep] = []
    week = 1
    for order, (skill_id, course_ids, reason) in enumerate(PLANS.get(role_id, []), start=1):
        courses = [COURSES[c] for c in course_ids]
        hours = sum(c.hours for c in courses)
        weeks = max(1, -(-int(hours) // max(hours_per_week, 1)))
        result.append(
            PathwayStep(
                order=order,
                skill_id=skill_id,
                courses=courses,
                est_hours=hours,
                week_start=week,
                week_end=week + weeks - 1,
                reason=reason,
            )
        )
        week += weeks
    return result
