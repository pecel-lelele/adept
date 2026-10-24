"""Synthetic personas loader (F4 evaluation harness & demo seed only).

Production matching code must NOT import this module.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.features.matching.scoring import MatchProfile

_SEED = Path(__file__).resolve().parents[4] / "data" / "seed"


def load_persona_profile(user_id: str) -> MatchProfile | None:
    """Build MatchProfile from persona seed files (user_skills.csv, profiles.csv)."""
    # Interests from profiles.csv
    found = False
    interests: set[str] = set()
    profiles_path = _SEED / "personas" / "profiles.csv"
    if profiles_path.exists():
        with open(profiles_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["user_id"] == user_id:
                    raw = row["interests"].strip("{}")
                    interests = {t.strip() for t in raw.split(",") if t.strip()}
                    found = True
                    break
    if not found:
        return None

    # Keep the same 1-5 proficiency scale as the saved-profile production adapter.
    skills: dict[str, float] = {}
    user_skills_path = _SEED / "personas" / "user_skills.csv"
    if user_skills_path.exists():
        with open(user_skills_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["user_id"] == user_id:
                    lvl = int(row["level"])
                    skills[row["skill_id"]] = float(lvl)

    return MatchProfile(skills=skills, interests=frozenset(interests))


def load_expected_roles() -> dict[str, dict[str, float]]:
    """Load ground-truth relevance (user_id -> role_id -> relevance) for the benchmark.

    Single source of truth for expected_roles.csv so the benchmark tests do not
    carry their own copy of the loader.
    """
    gt: dict[str, dict[str, float]] = {}
    path = _SEED / "personas" / "expected_roles.csv"
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gt.setdefault(row["user_id"], {})[row["role_id"]] = float(row["relevance"])
    return gt


def load_all_personas() -> dict[str, MatchProfile]:
    """Load all synthetic personas from seed CSV files."""
    personas: dict[str, MatchProfile] = {}
    profiles_path = _SEED / "personas" / "profiles.csv"
    if profiles_path.exists():
        with open(profiles_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["user_id"]
                p = load_persona_profile(uid)
                if p is not None:
                    personas[uid] = p
    return personas
