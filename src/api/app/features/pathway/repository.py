"""State for pathways: saved plans, course progress, earned badges.

Two stores behind the same functions (chosen by `M3_BACKEND`, see `app.core.refdata`):

- `MemoryStore` (csv, default): per process, for local dev and tests.
- `PostgresStore` (postgres): tables `pathway_plans`, `course_progress`, `user_badges`, so
  plans survive restarts and every API instance sees the same state.

Reference data (catalogue, taxonomy, trends) lives in `data.py`.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from app.contracts.pathway import CourseStatus, Pathway, SavedPlan
from app.core.db import connection
from app.core.refdata import StorageUnavailableError, use_postgres


class Store(Protocol):
    def get_plan(self, user_id: str) -> SavedPlan | None: ...
    def save_plan(self, user_id: str, plan: SavedPlan) -> SavedPlan: ...
    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]: ...
    def set_course_status(
        self, user_id: str, role_id: str, course_id: str, status: CourseStatus
    ) -> None: ...
    def record_badges(self, user_id: str, badge_ids: list[str], today: date) -> dict[str, date]: ...
    def reset(self) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._plans: dict[str, SavedPlan] = {}
        self._progress: dict[tuple[str, str], dict[str, CourseStatus]] = {}
        self._badges: dict[str, dict[str, date]] = {}

    def get_plan(self, user_id: str) -> SavedPlan | None:
        return self._plans.get(user_id)

    def save_plan(self, user_id: str, plan: SavedPlan) -> SavedPlan:
        self._plans[user_id] = plan
        return plan

    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]:
        return dict(self._progress.get((user_id, role_id), {}))

    def set_course_status(
        self, user_id: str, role_id: str, course_id: str, status: CourseStatus
    ) -> None:
        statuses = self._progress.setdefault((user_id, role_id), {})
        if status == "not_started":
            statuses.pop(course_id, None)
        else:
            statuses[course_id] = status

    def record_badges(self, user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
        earned = self._badges.setdefault(user_id, {})
        for badge_id in badge_ids:
            earned.setdefault(badge_id, today)
        return dict(earned)

    def reset(self) -> None:
        self._plans.clear()
        self._progress.clear()
        self._badges.clear()


class PostgresStore:
    """Plans are stored whole (the `steps` jsonb column holds the full Pathway) so a saved
    plan is exactly what the learner saw, even after the catalogue or trends change."""

    def _run(self, sql: str, params: tuple[object, ...]) -> list[tuple[object, ...]]:
        try:
            with connection() as conn, conn.cursor(row_factory=tuple_row) as cur:
                cur.execute(sql, params)  # type: ignore[arg-type]
                return list(cur.fetchall()) if cur.description else []
        except psycopg.Error as exc:
            raise StorageUnavailableError(type(exc).__name__) from exc

    def _ensure_user(self, user_id: str) -> None:
        # Supabase users have no row yet; demo personas are seeded. Never mark as synthetic.
        self._run(
            "INSERT INTO users (id, display_name, kind, is_synthetic) "
            "VALUES (%s, %s, 'learner', false) ON CONFLICT (id) DO NOTHING",
            (user_id, user_id),
        )

    def get_plan(self, user_id: str) -> SavedPlan | None:
        rows = self._run(
            "SELECT role_id, scenario, snapshot_version, saved_at, steps "
            "FROM pathway_plans WHERE user_id = %s",
            (user_id,),
        )
        if not rows:
            return None
        role_id, scenario, version, saved_at, pathway = rows[0]
        return SavedPlan(
            role_id=str(role_id),
            scenario=scenario,  # type: ignore[arg-type]
            snapshot_version=str(version),
            saved_at=saved_at,  # type: ignore[arg-type]
            pathway=Pathway.model_validate(pathway),
        )

    def save_plan(self, user_id: str, plan: SavedPlan) -> SavedPlan:
        self._ensure_user(user_id)
        self._run(
            "INSERT INTO pathway_plans (user_id, role_id, scenario, snapshot_version, steps, "
            "saved_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET "
            "role_id = EXCLUDED.role_id, scenario = EXCLUDED.scenario, "
            "snapshot_version = EXCLUDED.snapshot_version, steps = EXCLUDED.steps, "
            "saved_at = EXCLUDED.saved_at",
            (
                user_id,
                plan.role_id,
                plan.scenario,
                plan.snapshot_version,
                Jsonb(plan.pathway.model_dump(mode="json")),
                plan.saved_at,
            ),
        )
        return plan

    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]:
        rows = self._run(
            "SELECT course_id, status FROM course_progress WHERE user_id = %s AND role_id = %s",
            (user_id, role_id),
        )
        return {str(cid): status for cid, status in rows}  # type: ignore[misc]

    def set_course_status(
        self, user_id: str, role_id: str, course_id: str, status: CourseStatus
    ) -> None:
        if status == "not_started":
            self._run(
                "DELETE FROM course_progress WHERE user_id = %s AND role_id = %s "
                "AND course_id = %s",
                (user_id, role_id, course_id),
            )
            return
        self._ensure_user(user_id)
        self._run(
            "INSERT INTO course_progress (user_id, role_id, course_id, status) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, role_id, course_id) "
            "DO UPDATE SET status = EXCLUDED.status, updated_at = now()",
            (user_id, role_id, course_id, status),
        )

    def record_badges(self, user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
        if badge_ids:
            self._ensure_user(user_id)
        for badge_id in badge_ids:
            self._run(
                "INSERT INTO user_badges (user_id, badge_id, earned_at, evidence) "
                "VALUES (%s, %s, %s, 'self_reported') ON CONFLICT (user_id, badge_id) DO NOTHING",
                (user_id, badge_id, today),
            )
        rows = self._run(
            "SELECT badge_id, earned_at::date FROM user_badges WHERE user_id = %s", (user_id,)
        )
        return {str(b): d for b, d in rows}  # type: ignore[misc]

    def reset(self) -> None:
        """Test hook: clears pathway state (not users or reference data)."""
        for table in ("course_progress", "user_badges", "pathway_plans"):
            self._run(f"DELETE FROM {table}", ())


_MEMORY = MemoryStore()
_POSTGRES = PostgresStore()


def store() -> Store:
    return _POSTGRES if use_postgres() else _MEMORY


def get_plan(user_id: str) -> SavedPlan | None:
    return store().get_plan(user_id)


def save_plan(user_id: str, plan: SavedPlan) -> SavedPlan:
    return store().save_plan(user_id, plan)


def course_status(user_id: str, role_id: str) -> dict[str, CourseStatus]:
    return store().course_status(user_id, role_id)


def set_course_status(user_id: str, role_id: str, course_id: str, status: CourseStatus) -> None:
    store().set_course_status(user_id, role_id, course_id, status)


def record_badges(user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
    """Keep the first date each badge was earned; return all earned dates."""
    return store().record_badges(user_id, badge_ids, today)


def reset() -> None:
    """Test hook."""
    store().reset()
