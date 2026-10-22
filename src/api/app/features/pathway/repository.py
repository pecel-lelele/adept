"""State for pathways: saved plans, course progress, earned badges.

Two stores behind the same functions (chosen by `M3_BACKEND`, see `app.core.refdata`):

- `MemoryStore` (csv, default): per process, for local dev and tests.
- `PostgresStore` (postgres): tables `pathway_plans`, `course_progress`, `user_badges`, so
  plans survive restarts and every API instance sees the same state.

Reference data (catalogue, taxonomy, trends) lives in `data.py`.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from app.contracts.pathway import CompletionEvidence, Course, CourseStatus, Pathway, SavedPlan
from app.core.db import connection
from app.core.refdata import StorageUnavailableError, use_postgres


@dataclass(frozen=True)
class LearningRecord:
    user_id: str
    role_id: str
    course_id: str
    status: CourseStatus
    course: Course | None
    evidence: CompletionEvidence | None


def _plan_key(plan: SavedPlan) -> str:
    return hashlib.sha256(plan.pathway.model_dump_json().encode()).hexdigest()


class Store(Protocol):
    def get_plan(self, user_id: str) -> SavedPlan | None: ...
    def save_plan(self, user_id: str, plan: SavedPlan) -> SavedPlan: ...
    def plan_history(self, user_id: str) -> list[SavedPlan]: ...
    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]: ...
    def course_facts(self, user_id: str, role_id: str) -> dict[str, Course]: ...
    def set_course_status(
        self,
        user_id: str,
        role_id: str,
        course_id: str,
        status: CourseStatus,
        course: Course | None = None,
    ) -> None: ...
    def record_badges(self, user_id: str, badge_ids: list[str], today: date) -> dict[str, date]: ...
    def evidence(self, user_id: str, role_id: str) -> dict[str, CompletionEvidence]: ...
    def save_evidence(self, user_id: str, ev: CompletionEvidence) -> None: ...
    def delete_evidence(self, user_id: str, role_id: str, course_id: str) -> None: ...
    def review_evidence(
        self, user_id: str, ev: CompletionEvidence, seen: datetime | None
    ) -> bool: ...
    def progress_of(self, user_ids: list[str]) -> list[tuple[str, str, str, CourseStatus]]: ...
    def learning_records(self, user_ids: list[str]) -> list[LearningRecord]: ...
    def reset(self) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._plans: dict[str, SavedPlan] = {}
        self._plan_history: dict[tuple[str, str], SavedPlan] = {}
        self._progress: dict[tuple[str, str], dict[str, CourseStatus]] = {}
        self._badges: dict[str, dict[str, date]] = {}
        self._evidence: dict[tuple[str, str, str], CompletionEvidence] = {}
        self._course_facts: dict[tuple[str, str, str], Course] = {}
        self._lock = threading.Lock()

    def get_plan(self, user_id: str) -> SavedPlan | None:
        return self._plans.get(user_id)

    def save_plan(self, user_id: str, plan: SavedPlan) -> SavedPlan:
        self._plan_history.setdefault((user_id, _plan_key(plan)), plan.model_copy(deep=True))
        self._plans[user_id] = plan
        return plan

    def plan_history(self, user_id: str) -> list[SavedPlan]:
        return [
            plan.model_copy(deep=True)
            for (uid, _key), plan in self._plan_history.items()
            if uid == user_id
        ]

    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]:
        return dict(self._progress.get((user_id, role_id), {}))

    def set_course_status(
        self,
        user_id: str,
        role_id: str,
        course_id: str,
        status: CourseStatus,
        course: Course | None = None,
    ) -> None:
        statuses = self._progress.setdefault((user_id, role_id), {})
        key = (user_id, role_id, course_id)
        if status == "not_started":
            statuses.pop(course_id, None)
            self._course_facts.pop(key, None)
        else:
            statuses[course_id] = status
            if course is not None:
                self._course_facts.setdefault(key, course.model_copy(deep=True))

    def course_facts(self, user_id: str, role_id: str) -> dict[str, Course]:
        return {
            cid: course.model_copy(deep=True)
            for (uid, rid, cid), course in self._course_facts.items()
            if uid == user_id and rid == role_id
        }

    def record_badges(self, user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
        earned = self._badges.setdefault(user_id, {})
        for badge_id in badge_ids:
            earned.setdefault(badge_id, today)
        return dict(earned)

    def evidence(self, user_id: str, role_id: str) -> dict[str, CompletionEvidence]:
        return {
            course: ev
            for (uid, rid, course), ev in self._evidence.items()
            if uid == user_id and rid == role_id
        }

    def save_evidence(self, user_id: str, ev: CompletionEvidence) -> None:
        self._evidence[(user_id, ev.role_id, ev.course_id)] = ev

    def delete_evidence(self, user_id: str, role_id: str, course_id: str) -> None:
        self._evidence.pop((user_id, role_id, course_id), None)

    def review_evidence(self, user_id: str, ev: CompletionEvidence, seen: datetime | None) -> bool:
        key = (user_id, ev.role_id, ev.course_id)
        with self._lock:
            current = self._evidence.get(key)
            if (current.submitted_at if current else None) != seen:
                return False
            self._evidence[key] = ev
            return True

    def progress_of(self, user_ids: list[str]) -> list[tuple[str, str, str, CourseStatus]]:
        wanted = set(user_ids)
        return [
            (uid, rid, cid, status)
            for (uid, rid), statuses in self._progress.items()
            if uid in wanted
            for cid, status in statuses.items()
        ]

    def learning_records(self, user_ids: list[str]) -> list[LearningRecord]:
        return [
            LearningRecord(
                uid, rid, cid, status,
                self._course_facts.get((uid, rid, cid)),
                self._evidence.get((uid, rid, cid)),
            )
            for uid, rid, cid, status in self.progress_of(user_ids)
        ]  # fmt: skip

    def reset(self) -> None:
        self._plans.clear()
        self._plan_history.clear()
        self._progress.clear()
        self._badges.clear()
        self._evidence.clear()
        self._course_facts.clear()


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
            "WITH archived AS (INSERT INTO pathway_plan_history "
            "(user_id, plan_key, role_id, scenario, snapshot_version, steps, saved_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (user_id, plan_key) DO NOTHING) "
            "INSERT INTO pathway_plans (user_id, role_id, scenario, snapshot_version, steps, "
            "saved_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET "
            "role_id = EXCLUDED.role_id, scenario = EXCLUDED.scenario, "
            "snapshot_version = EXCLUDED.snapshot_version, steps = EXCLUDED.steps, "
            "saved_at = EXCLUDED.saved_at",
            (
                user_id,
                _plan_key(plan),
                plan.role_id,
                plan.scenario,
                plan.snapshot_version,
                Jsonb(plan.pathway.model_dump(mode="json")),
                plan.saved_at,
                user_id,
                plan.role_id,
                plan.scenario,
                plan.snapshot_version,
                Jsonb(plan.pathway.model_dump(mode="json")),
                plan.saved_at,
            ),
        )
        return plan

    def plan_history(self, user_id: str) -> list[SavedPlan]:
        rows = self._run(
            "SELECT role_id, scenario, snapshot_version, saved_at, steps "
            "FROM pathway_plan_history WHERE user_id = %s ORDER BY saved_at, plan_key",
            (user_id,),
        )
        return [
            SavedPlan(
                role_id=str(role), scenario=scenario, snapshot_version=str(version),
                saved_at=saved_at, pathway=Pathway.model_validate(pathway),
            )
            for role, scenario, version, saved_at, pathway in rows
        ]  # fmt: skip

    def course_status(self, user_id: str, role_id: str) -> dict[str, CourseStatus]:
        rows = self._run(
            "SELECT course_id, status FROM course_progress WHERE user_id = %s AND role_id = %s",
            (user_id, role_id),
        )
        return {str(cid): status for cid, status in rows}  # type: ignore[misc]

    def set_course_status(
        self,
        user_id: str,
        role_id: str,
        course_id: str,
        status: CourseStatus,
        course: Course | None = None,
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
            "INSERT INTO course_progress (user_id, role_id, course_id, status, course_snapshot) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id, role_id, course_id) "
            "DO UPDATE SET status = EXCLUDED.status, updated_at = now(), "
            "course_snapshot = COALESCE(course_progress.course_snapshot, EXCLUDED.course_snapshot)",
            (
                user_id,
                role_id,
                course_id,
                status,
                Jsonb(course.model_dump(mode="json")) if course is not None else None,
            ),
        )

    def course_facts(self, user_id: str, role_id: str) -> dict[str, Course]:
        rows = self._run(
            "SELECT course_id, course_snapshot FROM course_progress "
            "WHERE user_id = %s AND role_id = %s AND course_snapshot IS NOT NULL",
            (user_id, role_id),
        )
        return {str(cid): Course.model_validate(facts) for cid, facts in rows}

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

    _EVIDENCE_COLS = (
        "role_id, course_id, kind, url, link_status, link_checked_at, submitted_at, "
        "reviewed_by, reviewed_at, review_note"
    )

    def evidence(self, user_id: str, role_id: str) -> dict[str, CompletionEvidence]:
        rows = self._run(
            f"SELECT {self._EVIDENCE_COLS} FROM course_evidence "
            "WHERE user_id = %s AND role_id = %s",
            (user_id, role_id),
        )
        names = [c.strip() for c in self._EVIDENCE_COLS.split(",")]
        out: dict[str, CompletionEvidence] = {}
        for row in rows:
            ev = CompletionEvidence.model_validate(dict(zip(names, row, strict=True)))
            out[ev.course_id] = ev
        return out

    def save_evidence(self, user_id: str, ev: CompletionEvidence) -> None:
        self._ensure_user(user_id)
        if ev.reviewed_by:
            self._ensure_user(ev.reviewed_by)
        self._run(
            f"INSERT INTO course_evidence (user_id, {self._EVIDENCE_COLS}) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (user_id, role_id, course_id) DO UPDATE SET kind = EXCLUDED.kind, "
            "url = EXCLUDED.url, link_status = EXCLUDED.link_status, "
            "link_checked_at = EXCLUDED.link_checked_at, submitted_at = EXCLUDED.submitted_at, "
            "reviewed_by = EXCLUDED.reviewed_by, reviewed_at = EXCLUDED.reviewed_at, "
            "review_note = EXCLUDED.review_note",
            (
                user_id, ev.role_id, ev.course_id, ev.kind, ev.url, ev.link_status,
                ev.link_checked_at, ev.submitted_at, ev.reviewed_by, ev.reviewed_at,
                ev.review_note,
            ),
        )  # fmt: skip

    def delete_evidence(self, user_id: str, role_id: str, course_id: str) -> None:
        self._run(
            "DELETE FROM course_evidence WHERE user_id = %s AND role_id = %s AND course_id = %s",
            (user_id, role_id, course_id),
        )

    def review_evidence(self, user_id: str, ev: CompletionEvidence, seen: datetime | None) -> bool:
        """Save a review only if the stored submission is still the one the reviewer saw."""
        if ev.reviewed_by:
            self._ensure_user(ev.reviewed_by)
        if seen is None:  # nothing was stored: insert, unless something arrived meanwhile
            self._ensure_user(user_id)
            rows = self._run(
                f"INSERT INTO course_evidence (user_id, {self._EVIDENCE_COLS}) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (user_id, role_id, course_id) DO NOTHING RETURNING 1",
                (
                    user_id, ev.role_id, ev.course_id, ev.kind, ev.url, ev.link_status,
                    ev.link_checked_at, ev.submitted_at, ev.reviewed_by, ev.reviewed_at,
                    ev.review_note,
                ),
            )  # fmt: skip
            return bool(rows)
        rows = self._run(
            "UPDATE course_evidence SET kind = %s, reviewed_by = %s, reviewed_at = %s, "
            "review_note = %s WHERE user_id = %s AND role_id = %s AND course_id = %s "
            "AND submitted_at = %s RETURNING 1",
            (
                ev.kind, ev.reviewed_by, ev.reviewed_at, ev.review_note,
                user_id, ev.role_id, ev.course_id, seen,
            ),
        )  # fmt: skip
        return bool(rows)

    def progress_of(self, user_ids: list[str]) -> list[tuple[str, str, str, CourseStatus]]:
        if not user_ids:
            return []
        rows = self._run(
            "SELECT user_id, role_id, course_id, status FROM course_progress "
            "WHERE user_id = ANY(%s) ORDER BY user_id, role_id, course_id",
            (user_ids,),
        )
        return [(str(u), str(r), str(c), s) for u, r, c, s in rows]  # type: ignore[misc]

    def learning_records(self, user_ids: list[str]) -> list[LearningRecord]:
        if not user_ids:
            return []
        rows = self._run(
            "SELECT p.user_id, p.role_id, p.course_id, p.status, p.course_snapshot, "
            "CASE WHEN e.user_id IS NULL THEN NULL ELSE to_jsonb(e) END "
            "FROM course_progress p LEFT JOIN course_evidence e "
            "ON (e.user_id, e.role_id, e.course_id) = (p.user_id, p.role_id, p.course_id) "
            "WHERE p.user_id = ANY(%s) ORDER BY p.user_id, p.role_id, p.course_id",
            (user_ids,),
        )
        return [
            LearningRecord(
                str(uid), str(rid), str(cid), status,
                Course.model_validate(facts) if facts is not None else None,
                CompletionEvidence.model_validate(evidence) if evidence is not None else None,
            )
            for uid, rid, cid, status, facts, evidence in rows
        ]  # fmt: skip

    def reset(self) -> None:
        """Test hook: clears pathway state (not users or reference data)."""
        for table in (
            "course_evidence",
            "course_progress",
            "user_badges",
            "pathway_plans",
            "pathway_plan_history",
        ):
            self._run(f"DELETE FROM {table}", ())


_MEMORY = MemoryStore()
_POSTGRES = PostgresStore()


def store() -> Store:
    return _POSTGRES if use_postgres() else _MEMORY


def get_plan(user_id: str) -> SavedPlan | None:
    return store().get_plan(user_id)


def save_plan(user_id: str, plan: SavedPlan) -> SavedPlan:
    return store().save_plan(user_id, plan)


def plan_history(user_id: str) -> list[SavedPlan]:
    """Prior plan contexts keep earned badges independent of the remaining plan."""
    return store().plan_history(user_id)


def course_status(user_id: str, role_id: str) -> dict[str, CourseStatus]:
    return store().course_status(user_id, role_id)


def set_course_status(
    user_id: str,
    role_id: str,
    course_id: str,
    status: CourseStatus,
    course: Course | None = None,
) -> None:
    store().set_course_status(user_id, role_id, course_id, status, course)


def course_facts(user_id: str, role_id: str) -> dict[str, Course]:
    """Immutable course facts captured with progress, independent of the current target."""
    return store().course_facts(user_id, role_id)


def record_badges(user_id: str, badge_ids: list[str], today: date) -> dict[str, date]:
    """Keep the first date each badge was earned; return all earned dates."""
    return store().record_badges(user_id, badge_ids, today)


def evidence(user_id: str, role_id: str) -> dict[str, CompletionEvidence]:
    return store().evidence(user_id, role_id)


def save_evidence(user_id: str, ev: CompletionEvidence) -> None:
    store().save_evidence(user_id, ev)


def delete_evidence(user_id: str, role_id: str, course_id: str) -> None:
    store().delete_evidence(user_id, role_id, course_id)


def review_evidence(user_id: str, ev: CompletionEvidence, seen: datetime | None) -> bool:
    """Apply a review atomically; False if the evidence changed since `seen`."""
    return store().review_evidence(user_id, ev, seen)


def progress_of(user_ids: list[str]) -> list[tuple[str, str, str, CourseStatus]]:
    """(user, role, course, status) rows for these users (for HR / advisor review)."""
    return store().progress_of(user_ids)


def learning_records(user_ids: list[str]) -> list[LearningRecord]:
    """Batch progress, immutable course facts and evidence in one store read."""
    return store().learning_records(user_ids)


def reset() -> None:
    """Test hook."""
    store().reset()
