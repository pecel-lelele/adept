"""Data access for profiles (F1).

Profiles live in PostgreSQL (`users`, `profiles`, `user_skills`; `M3_BACKEND=postgres`, the
default), so a saved questionnaire or confirmed skill list survives restarts and every API
instance sees the same profile. If the database is unreachable, reads and writes fail with
503: a user is never shown or told about data that is not actually stored.

`M3_BACKEND=csv` swaps in an in-memory dict for the automated tests only (`_store`); it
starts empty, there are no built-in personas.
"""

from __future__ import annotations

from typing import Any

import psycopg

from app.contracts.profile import Profile, UserSkill
from app.core.db import connection
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.refdata import StorageUnavailableError, use_postgres

log = get_logger("app.profile.repository")

# Test-only memory store (M3_BACKEND=csv). Tests snapshot and restore this dict directly.
_store: dict[str, Profile] = {}

_SELECT_PROFILE = """
    SELECT u.id, u.display_name, p.segment, p.interests, p.hours_per_week, p.budget_myr,
           p.hrd_eligible, p.current_role_id, p.learning_style
    FROM profiles p JOIN users u ON u.id = p.user_id
    WHERE p.user_id = %s
"""
_SELECT_SKILLS = """
    SELECT skill_id, level, source FROM user_skills WHERE user_id = %s ORDER BY skill_id
"""


def _row_to_profile(row: dict[str, Any], skills: list[dict[str, Any]]) -> Profile:
    return Profile(
        user_id=str(row["id"]),
        display_name=str(row["display_name"]),
        segment=row["segment"],
        interests=list(row["interests"] or []),
        hours_per_week=int(row["hours_per_week"]),
        budget_myr=float(row["budget_myr"]),
        hrd_eligible=bool(row["hrd_eligible"]),
        learning_style=row.get("learning_style") or "mixed",
        current_role_id=row["current_role_id"],
        skills=[
            UserSkill(skill_id=str(s["skill_id"]), level=int(s["level"]), source=s["source"])
            for s in skills
        ],
    )


def _db_get(user_id: str) -> Profile | None:
    with connection() as conn:
        row = conn.execute(_SELECT_PROFILE, (user_id,)).fetchone()
        if row is None:
            return None
        skills = conn.execute(_SELECT_SKILLS, (user_id,)).fetchall()
    return _row_to_profile(row, skills)


def _db_save(profile: Profile) -> None:
    with connection() as conn, conn.transaction():
        # A Supabase user has no seeded `users` row yet; create it on first save.
        conn.execute(
            """
            INSERT INTO users (id, display_name, kind, is_synthetic)
            VALUES (%s, %s, 'learner', true)
            ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name
            """,
            (profile.user_id, profile.display_name),
        )
        conn.execute(
            """
            INSERT INTO profiles (user_id, segment, interests, hours_per_week, budget_myr,
                                  hrd_eligible, current_role_id, learning_style, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                segment = EXCLUDED.segment,
                interests = EXCLUDED.interests,
                hours_per_week = EXCLUDED.hours_per_week,
                budget_myr = EXCLUDED.budget_myr,
                hrd_eligible = EXCLUDED.hrd_eligible,
                current_role_id = EXCLUDED.current_role_id,
                learning_style = EXCLUDED.learning_style,
                updated_at = now()
            """,
            (
                profile.user_id,
                profile.segment,
                profile.interests,
                profile.hours_per_week,
                profile.budget_myr,
                profile.hrd_eligible,
                profile.current_role_id,
                profile.learning_style,
            ),
        )
        # The submitted list replaces the previous one (confirmation screen semantics).
        conn.execute("DELETE FROM user_skills WHERE user_id = %s", (profile.user_id,))
        if profile.skills:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO user_skills (user_id, skill_id, level, source) "
                    "VALUES (%s, %s, %s, %s)",
                    [(profile.user_id, s.skill_id, s.level, s.source) for s in profile.skills],
                )


def get_profile(user_id: str) -> Profile | None:
    if not use_postgres():
        return _store.get(user_id)
    try:
        return _db_get(user_id)
    except psycopg.Error as exc:
        log.warning("profile read failed: %s", exc)
        raise StorageUnavailableError("could not load the profile") from exc


def save_profile(profile: Profile) -> Profile:
    if not use_postgres():
        _store[profile.user_id] = profile
        return profile
    try:
        _db_save(profile)
    except psycopg.errors.ForeignKeyViolation as exc:
        # Unknown role or skill id: a client bug, not an outage.
        raise AppError(
            "Your profile refers to a role or skill that is not in the catalogue.",
            status_code=422,
            code="unknown_reference",
        ) from exc
    except psycopg.Error as exc:
        raise StorageUnavailableError("could not save the profile") from exc
    return profile
