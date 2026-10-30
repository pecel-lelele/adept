"""Explainable role-matching score (M2-06, M2-07).

score = w_skill * skill_overlap + w_trend * trend + w_interest * interest_contribution

interest_fit is a real Jaccard, len(interests & tags) / len(interests | tags).
When the user gave no interests, interest_fit is None ("not provided") and the
total uses the neutral contribution NEUTRAL = 0.5 instead.

Pure functions, no I/O, so they are easy to test and to evaluate (M2-09).
`MatchProfile` is the fairness whitelist (M2-12): only these fields can ever
reach the score. Age, gender and background are not part of it on purpose.

NOTE for the service bridge and evaluation harness:
  Preserve UserSkill.level on its 1–5 scale to compare with required_level.
  An absent skill has level 0; skill_credit maps proficiency to a 0–1 credit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

NEUTRAL = 0.5  # used when there is no data, and reported through `trend_coverage`


@dataclass(frozen=True)
class Weights:
    skill: float = 0.45
    trend: float = 0.25
    interest: float = 0.30


@dataclass(frozen=True)
class RoleSkill:
    skill_id: str
    importance: float  # 0..1
    required_level: int = 1  # 1..5, defaults to 1 for backward compatibility


@dataclass(frozen=True)
class Role:
    role_id: str
    skills: tuple[RoleSkill, ...]
    interest_tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MatchProfile:
    skills: dict[str, float]  # skill_id -> proficiency 1..5; absent skills default to 0
    interests: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _RoleScore:
    """Internal result of the scoring engine.

    This is NOT the API contract type; the service maps it to
    ``contracts.matching.RoleMatch`` (which adds label, sdg_targets, meta).
    """

    role_id: str
    score: float
    breakdown: dict[str, float | None]  # keys: "skill" / "trend" / "interest", each 0..1 or None
    gap: dict[str, list[str]]  # buckets: "have" / "partial" / "missing"
    trend_coverage: float = 1.0  # share of role skill weight that had trend data


# Same bound the trend pipeline applies to both scenario velocities (pipelines/trends/score.py).
VELOCITY_CLAMP = 2.0


def _clamped(value: float) -> float:
    return max(-VELOCITY_CLAMP, min(VELOCITY_CLAMP, value))


def trend_scores(
    velocities: dict[str, float], reference_velocities: dict[str, float] | None = None
) -> dict[str, float]:
    """Robust 0..1 trend position on one scale shared by both scenarios.

    position(v) = 0.5 + 0.5 * tanh(clamp(v, ±2) / s), s = median |v| over the union of both
    scenarios' clamped velocities. Zero velocity is neutral (0.5), rising skills sit above it,
    declining below. Min-max let a few large velocities stretch the range so most skills
    collapsed into ~0.577; the median scale keeps the bulk separated while outliers saturate.

    A snapshot already contains both scenarios; its adapter supplies the other one, so the
    scale is the same for Moderate and Fast and Fast >= Moderate wherever v_fast >= v_mod.
    Pure offline callers may supply one set only. All-zero velocities are neutral.
    """
    values = [_clamped(v) for v in (*velocities.values(), *(reference_velocities or {}).values())]
    if not values:
        return {}
    magnitudes = sorted(abs(v) for v in values)
    middle = len(magnitudes) // 2
    scale = (
        magnitudes[middle]
        if len(magnitudes) % 2
        else (magnitudes[middle - 1] + magnitudes[middle]) / 2
    )
    if scale <= 0:
        scale = magnitudes[-1]
    if scale <= 0:
        return {skill: NEUTRAL for skill in velocities}
    return {
        skill: 0.5 + 0.5 * math.tanh(_clamped(value) / scale) for skill, value in velocities.items()
    }


def gap_state(user_level: float | int, required_level: int = 1) -> str:
    """Gap state in integer levels 1-5:

    - 'have' if user_level >= required_level
    - 'partial' if 0 < user_level < required_level
    - 'missing' if user_level <= 0 (not in profile)
    """
    if user_level <= 0:
        return "missing"
    if user_level >= required_level:
        return "have"
    return "partial"


def skill_credit(user_level: float | int, required_level: int = 1) -> float:
    """Credit per skill = min(user_level / required_level, 1.0).

    Overlap and gap never disagree:
    - have: credit == 1.0
    - partial: 0.0 < credit < 1.0
    - missing: credit == 0.0
    """
    if required_level <= 0 or user_level <= 0:
        return 0.0
    return min(user_level / required_level, 1.0)


def skill_overlap(profile: MatchProfile, role: Role) -> float:
    total = sum(rs.importance for rs in role.skills)
    if total == 0:
        return 0.0
    credit_sum = sum(
        rs.importance * skill_credit(profile.skills.get(rs.skill_id, 0.0), rs.required_level)
        for rs in role.skills
    )
    return credit_sum / total


def role_trend(role: Role, scores: dict[str, float]) -> tuple[float, float]:
    """Importance-weighted trend of the role's skills. Returns (trend, coverage)."""
    total = sum(rs.importance for rs in role.skills)
    if total == 0:
        return NEUTRAL, 0.0
    covered = sum(rs.importance for rs in role.skills if rs.skill_id in scores)
    value = sum(rs.importance * scores.get(rs.skill_id, NEUTRAL) for rs in role.skills) / total
    return value, covered / total


def interest_fit(profile: MatchProfile, role: Role) -> float | None:
    """Jaccard similarity between user interests and role interest tags.

    Formula: len(interests & tags) / len(interests | tags)

    Returns:
        float in [0.0, 1.0] representing Jaccard overlap.
        None if the user has no interests recorded (not provided), in which case
        downstream scoring applies a neutral contribution of 0.5 in the total score.
    """
    if not profile.interests:
        return None
    union = profile.interests | role.interest_tags
    if not union:
        return 0.0
    return len(profile.interests & role.interest_tags) / len(union)


def skills_gap(profile: MatchProfile, role: Role) -> dict[str, list[str]]:
    gap: dict[str, list[str]] = {"have": [], "partial": [], "missing": []}
    for rs in role.skills:
        user_level = profile.skills.get(rs.skill_id, 0.0)
        bucket = gap_state(user_level, rs.required_level)
        gap[bucket].append(rs.skill_id)
    return gap


def score_role(
    profile: MatchProfile,
    role: Role,
    scores: dict[str, float],
    w: Weights,
) -> _RoleScore:
    s = skill_overlap(profile, role)
    t, coverage = role_trend(role, scores)
    i = interest_fit(profile, role)
    i_contrib = NEUTRAL if i is None else i
    return _RoleScore(
        role_id=role.role_id,
        score=w.skill * s + w.trend * t + w.interest * i_contrib,
        breakdown={"skill": s, "trend": t, "interest": i},
        gap=skills_gap(profile, role),
        trend_coverage=coverage,
    )


_DEFAULT_WEIGHTS = Weights()  # module-level singleton — avoids B008


def rank_roles(
    profile: MatchProfile,
    roles: list[Role],
    velocities: dict[str, float],
    w: Weights = _DEFAULT_WEIGHTS,
    *,
    reference_velocities: dict[str, float] | None = None,
) -> list[_RoleScore]:
    """Score and rank roles. Tie-break on role_id for determinism (M2-13)."""
    scores = trend_scores(velocities, reference_velocities)
    matches = [score_role(profile, r, scores, w) for r in roles]
    return sorted(matches, key=lambda m: (-m.score, m.role_id))
