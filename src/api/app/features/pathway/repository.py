"""State for pathways: saved plans, course progress, earned badges.

In-memory per process (like the profile feature) so the demo runs without a database; the
matching tables are `pathway_plans`, `course_progress` and `user_badges`
(migration 20261020120000). Reference data (catalogue, taxonomy, trends) lives in `data.py`.
"""

from __future__ import annotations

from datetime import date

from app.contracts.pathway import CourseStatus, SavedPlan

_plans: dict[str, SavedPlan] = {}
_progress: dict[tuple[str, str], dict[str, CourseStatus]] = {}  # (user, role) -> course -> status
_badges: dict[str, dict[str, date]] = {}  # user -> badge id -> earned_at


def get_plan(user_id: str) -> SavedPlan | None:
    return _plans.get(user_id)


def save_plan(user_id: str, plan: SavedPlan) -> SavedPlan:
    _plans[user_id] = plan
    return plan


def course_status(user_id: str, role_id: str) -> dict[str, CourseStatus]:
    return dict(_progress.get((user_id, role_id), {}))


def set_course_status(user_id: str, role_id: str, course_id: str, status: CourseStatus) -> None:
    statuses = _progress.setdefault((user_id, role_id), {})
    if status == "not_started":
        statuses.pop(course_id, None)
    else:
        statuses[course_id] = status


def badge_dates(user_id: str) -> dict[str, date]:
    return dict(_badges.get(user_id, {}))


def record_badges(user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
    """Keep the first date each badge was earned; return all earned dates."""
    earned = _badges.setdefault(user_id, {})
    for badge_id in badge_ids:
        earned.setdefault(badge_id, today)
    return dict(earned)


def reset() -> None:
    """Test hook."""
    _plans.clear()
    _progress.clear()
    _badges.clear()
