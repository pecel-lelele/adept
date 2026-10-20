"""Data access for matching (F4).

Reads taxonomy and persona seed files, runs the real scoring engine, and
maps internal `_RoleScore` objects to the API contract type `RoleMatch`.

Falls back to mocks for unknown user IDs so the stub `/demo/org` flow
and contract tests keep working without seed rows.
"""

from __future__ import annotations

import csv
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.contracts.common import MOCK_SOURCE, RecommendationMeta, ScenarioId
from app.contracts.matching import RoleMatch, ScoreComponent
from app.contracts.profile import Skill
from app.contracts.sdg import SdgTarget
from app.features.matching import mocks
from app.features.matching.scoring import MatchProfile, Role, RoleSkill, Weights, rank_roles

_SEED = Path(__file__).resolve().parents[4] / "data" / "seed"

# Default weights (M2-001)
_W = Weights(skill=0.5, trend=0.3, interest=0.2)

# SDG badges sourced from M3-006 / M3-018 evidence mappings.
_ROLE_SDG: dict[str, list[SdgTarget]] = {
    "data-analyst": [
        SdgTarget(goal=4, target="4.4", label="Relevant skills for employment and decent jobs"),
        SdgTarget(goal=8, target="8.5", label="Full and productive employment for all"),
    ],
    "ai-operations-specialist": [
        SdgTarget(goal=8, target="8.2", label="Productivity through technology and innovation"),
        SdgTarget(goal=4, target="4.4", label="Relevant skills for employment and decent jobs"),
    ],
    "process-automation-analyst": [
        SdgTarget(goal=8, target="8.2", label="Productivity through technology and innovation"),
        SdgTarget(goal=4, target="4.4", label="Relevant skills for employment and decent jobs"),
    ],
    "compliance-analytics-officer": [
        SdgTarget(goal=8, target="8.5", label="Full and productive employment for all"),
    ],
}

# Interest tags inferred from profiles.csv and mocks (kept in repo so that the
# catalog is a pure CSV concern, without encoding UI strings in seed files).
_ROLE_INTEREST_TAGS: dict[str, frozenset[str]] = {
    "process-automation-analyst": frozenset(
        {"process improvement", "operations", "automation", "finance"}
    ),
    "data-analyst": frozenset({"data", "analytics", "software"}),
    "compliance-analytics-officer": frozenset({"finance", "risk", "data", "compliance"}),
    "ai-operations-specialist": frozenset({"software", "AI", "automation"}),
}

# Human-readable labels from roles.csv (loaded once below).
_ROLE_LABELS: dict[str, str] = {}
_SKILL_LABELS: dict[str, str] = {}


@lru_cache(maxsize=1)
def _load_roles() -> list[Role]:
    """Build Role objects from taxonomy seed CSV files (cached)."""
    global _ROLE_LABELS, _SKILL_LABELS  # noqa: PLW0603

    # Role labels
    roles_path = _SEED / "taxonomy" / "roles.csv"
    with open(roles_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _ROLE_LABELS[row["id"]] = row["label"]

    # Skill labels
    skills_path = _SEED / "taxonomy" / "skills.csv"
    with open(skills_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _SKILL_LABELS[row["id"]] = row["label"]

    # role_skills → Role objects
    skills_by_role: dict[str, list[RoleSkill]] = {}
    rs_path = _SEED / "taxonomy" / "role_skills.csv"
    with open(rs_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            skills_by_role.setdefault(row["role_id"], []).append(
                RoleSkill(skill_id=row["skill_id"], importance=float(row["importance"]))
            )

    return [
        Role(
            role_id=role_id,
            skills=tuple(skill_list),
            interest_tags=_ROLE_INTEREST_TAGS.get(role_id, frozenset()),
        )
        for role_id, skill_list in skills_by_role.items()
    ]


@lru_cache(maxsize=8)
def _load_profile(user_id: str) -> MatchProfile | None:
    """Build MatchProfile from persona seed files (cached per user_id)."""
    # Interests from profiles.csv
    found = False
    with open(_SEED / "personas" / "profiles.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["user_id"] == user_id:
                raw = row["interests"].strip("{}")
                interests = {t.strip() for t in raw.split(",") if t.strip()}
                found = True
                break
    if not found:
        return None  # user_id not found

    # Skills from user_skills.csv (normalise level 1-5 → 0..1)
    skills: dict[str, float] = {}
    with open(_SEED / "personas" / "user_skills.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["user_id"] == user_id:
                lvl = int(row["level"])
                skills[row["skill_id"]] = (lvl - 1) / 4.0

    return MatchProfile(skills=skills, interests=frozenset(interests))


def _score_to_contract(
    role_score: object,
    scenario: ScenarioId,
    snapshot_date: date,
) -> RoleMatch:
    """Map a scoring._RoleScore to the API contract RoleMatch."""
    # Ensure labels are populated
    _load_roles()

    role_id: str = role_score.role_id  # type: ignore[attr-defined]
    bd: dict[str, float] = role_score.breakdown  # type: ignore[attr-defined]
    gap: dict[str, list[str]] = role_score.gap  # type: ignore[attr-defined]

    def _skill_obj(sid: str) -> Skill:
        return Skill(id=sid, label=_SKILL_LABELS.get(sid, sid))

    components = [
        ScoreComponent(
            name="skill_overlap",
            weight=_W.skill,
            value=round(bd["skill"], 4),
            explanation="Share of required skills weighted by importance.",
        ),
        ScoreComponent(
            name="trend_outlook",
            weight=_W.trend,
            value=round(bd["trend"], 4),
            explanation=(
                f"Importance-weighted percentile rank of skill velocity ({scenario} scenario)."
            ),
        ),
        ScoreComponent(
            name="interest_fit",
            weight=_W.interest,
            value=round(bd["interest"], 4),
            explanation="Jaccard overlap between your interests and this role's tags.",
        ),
    ]

    return RoleMatch(
        role_id=role_id,
        label=_ROLE_LABELS.get(role_id, role_id),
        score=sum(c.weight * c.value for c in components),
        components=components,
        missing_skills=[_skill_obj(s) for s in gap.get("missing", [])],
        partial_skills=[_skill_obj(s) for s in gap.get("partial", [])],
        sdg_targets=_ROLE_SDG.get(role_id, []),
        meta=RecommendationMeta(
            sources=[MOCK_SOURCE],
            snapshot_date=snapshot_date,
            scenario=scenario,
            is_estimate=True,
        ),
    )


def list_matches(
    user_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    snapshot_date: date,
) -> list[RoleMatch]:
    """Run the real scoring engine and return ranked RoleMatch objects.

    Falls back to mocks if the user_id has no seed row.
    """
    profile = _load_profile(user_id)
    if profile is None:
        return mocks.matches(scenario)

    roles = _load_roles()
    ranked = rank_roles(profile, roles, velocities, _W)
    return [_score_to_contract(r, scenario, snapshot_date) for r in ranked]


def get_match(
    user_id: str,
    role_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    snapshot_date: date,
) -> RoleMatch | None:
    """Return the scored RoleMatch for a single role, or None if not found."""
    profile = _load_profile(user_id)
    if profile is None:
        return mocks.match(role_id, scenario)

    roles = _load_roles()
    ranked = rank_roles(profile, roles, velocities, _W)
    for r in ranked:
        if r.role_id == role_id:
            return _score_to_contract(r, scenario, snapshot_date)
    return None
