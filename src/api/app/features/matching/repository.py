"""Data access for matching (F4).

Reads taxonomy seed files and the saved profile, runs the real scoring engine, and
maps internal `_RoleScore` objects to the API contract type `RoleMatch`.

Missing profiles or skills raise ProfileRequiredError; production never loads personas.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.matching import RoleMatch, ScoreComponent
from app.contracts.profile import Skill
from app.core.errors import ProfileRequiredError
from app.features.matching.gap_port import fetch_skills_gap
from app.features.matching.scoring import (
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    _RoleScore,
    rank_roles,
)
from app.features.matching.sdg_port import fetch_role_badges
from app.features.profile import service as profile_service

_SEED = Path(__file__).resolve().parents[4] / "data" / "seed"

# Default weights — the canonical values live in scoring.Weights (M2-001, retuned in M2-011)
_W = Weights()

# Loaded from the canonical role catalogue by _load_roles.
_ROLE_INTEREST_TAGS: dict[str, frozenset[str]] = {}


def role_interest_tags(role_id: str) -> frozenset[str]:
    """Production getter for a role's interest tags (single source of truth).

    The evaluation benchmark and its tests must read tags through this
    function, never a copy of their own.
    """
    return _ROLE_INTEREST_TAGS.get(role_id, frozenset())


# Human-readable labels refreshed from the catalogue below.
_ROLE_LABELS: dict[str, str] = {}
_SKILL_LABELS: dict[str, str] = {}


def _load_roles() -> list[Role]:
    """Build Role objects from current taxonomy seed CSV files without a cache."""
    global _ROLE_LABELS, _SKILL_LABELS  # noqa: PLW0603

    # Role labels and interest tags from the canonical role catalogue.
    roles_path = _SEED / "taxonomy" / "roles.csv"
    with open(roles_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _ROLE_LABELS[row["id"]] = row["label"]
            _ROLE_INTEREST_TAGS[row["id"]] = frozenset(
                tag.strip() for tag in row.get("interest_tags", "").split("|") if tag.strip()
            )

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
                RoleSkill(
                    skill_id=row["skill_id"],
                    importance=float(row["importance"]),
                    required_level=int(row["required_level"]) if "required_level" in row else 1,
                )
            )

    return [
        Role(
            role_id=role_id,
            skills=tuple(skill_list),
            interest_tags=role_interest_tags(role_id),
        )
        for role_id, skill_list in skills_by_role.items()
    ]


def load_profile(user_id: str) -> MatchProfile:
    """Public entry point to the saved-profile loader (replay and other services)."""
    return _load_profile(user_id)


def role_label(role_id: str) -> str:
    _load_roles()
    return _ROLE_LABELS.get(role_id, role_id)


def skill_label(skill_id: str) -> str:
    _load_roles()
    return _SKILL_LABELS.get(skill_id, skill_id)


def load_roles() -> list[Role]:
    """Public entry point to the catalog loader (production + benchmark)."""
    return _load_roles()


def _load_profile(user_id: str) -> MatchProfile:
    """Build MatchProfile from saved profile (via profile_service.get_my_profile).

    Fairness whitelist (M2-12): only skills and interests are extracted.
    Demographic signals (age, gender, background) are never read here.
    No caching: edits to the profile take effect immediately.
    """
    if not profile_service.has_profile(user_id):
        raise ProfileRequiredError(
            f"Profile required: user '{user_id}' has no saved profile. "
            "Please complete your profile intake first."
        )
    profile = profile_service.get_my_profile(user_id)
    if not profile.skills:
        raise ProfileRequiredError(
            f"Profile required: user '{user_id}' has no saved skills. "
            "Please confirm your skills before matching roles."
        )

    # Use user's skill level (1-5 scale) directly for required_level comparison
    skills = {s.skill_id: float(s.level) for s in profile.skills}
    # Completed learning with accepted evidence (reviewer-confirmed, or a certificate on the
    # provider's verification page) raises a level; self-reported ticks do not (H08).
    from app.features.pathway import service as pathway_service

    for skill_id, level in pathway_service.evidenced_levels(user_id).items():
        skills[skill_id] = max(skills.get(skill_id, 0.0), float(level))
    interests = frozenset(profile.interests)

    return MatchProfile(skills=skills, interests=interests)


def _score_to_contract(
    role_score: _RoleScore,
    scenario: ScenarioId,
    meta: RecommendationMeta,
    user_levels: dict[str, int],
) -> RoleMatch:
    """Map a scoring._RoleScore to the API contract RoleMatch."""
    # Ensure labels are populated
    _load_roles()

    role_id = role_score.role_id
    bd = role_score.breakdown
    skill_value = bd["skill"]
    trend_value = bd["trend"]
    if skill_value is None or trend_value is None:
        raise ValueError("A scored role must have skill and trend values")

    # Gap status from unified gap port (pathway.service.skills_gap)
    gap = fetch_skills_gap(user_levels, role_id)

    def _skill_obj(sid: str) -> Skill:
        return Skill(id=sid, label=_SKILL_LABELS.get(sid, sid))

    components = [
        ScoreComponent(
            name="skill_overlap",
            weight=_W.skill,
            value=round(skill_value, 4),
            explanation="Share of required skills weighted by importance.",
        ),
        ScoreComponent(
            name="trend_outlook",
            weight=_W.trend,
            value=round(trend_value, 4),
            explanation=(
                f"Importance-weighted percentile rank of skill velocity ({scenario} scenario)."
            ),
        ),
        ScoreComponent(
            name="interest_fit",
            weight=_W.interest,
            value=(round(bd["interest"], 4) if bd["interest"] is not None else NEUTRAL),
            provided=bd["interest"] is not None,
            explanation=(
                "Jaccard similarity (intersection over union) between your interests and this"
                " role's tags."
                if bd["interest"] is not None
                else "Not provided: you have no saved interests, so a neutral 0.5 is used here."
            ),
        ),
    ]

    return RoleMatch(
        role_id=role_id,
        label=_ROLE_LABELS.get(role_id, role_id),
        score=sum(c.weight * c.value for c in components),
        components=components,
        missing_skills=[_skill_obj(s) for s in gap.get("missing", [])],
        partial_skills=[_skill_obj(s) for s in gap.get("partial", [])],
        sdg_targets=fetch_role_badges(role_id),
        trend_coverage=round(role_score.trend_coverage, 4),
        meta=meta,
    )


def list_matches(
    user_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    meta: RecommendationMeta,
) -> list[RoleMatch]:
    """Run the real scoring engine and return ranked RoleMatch objects."""
    profile = _load_profile(user_id)
    roles = _load_roles()
    ranked = rank_roles(profile, roles, velocities, _W)
    user_levels = {k: int(round(v)) for k, v in profile.skills.items()}
    return [_score_to_contract(r, scenario, meta, user_levels) for r in ranked]


def get_match(
    user_id: str,
    role_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    meta: RecommendationMeta,
) -> RoleMatch | None:
    """Return the scored RoleMatch for a single role, or None if not found."""
    profile = _load_profile(user_id)
    roles = _load_roles()
    ranked = rank_roles(profile, roles, velocities, _W)
    user_levels = {k: int(round(v)) for k, v in profile.skills.items()}
    for r in ranked:
        if r.role_id == role_id:
            return _score_to_contract(r, scenario, meta, user_levels)
    return None
