"""Explainable role-matching score (M2-06, M2-07).

score = w_skill * skill_overlap + w_trend * trend + w_interest * interest_fit

Pure functions, no I/O, so they are easy to test and to evaluate (M2-09).
`MatchProfile` is the fairness whitelist (M2-12): only these fields can ever
reach the score. Age, gender and background are not part of it on purpose.

NOTE for the service bridge:
  UserSkill.level is int 1–5; normalise before building MatchProfile:
      level_float = (level - 1) / 4   →  1→0.0, 3→0.5, 5→1.0
"""

from __future__ import annotations

from dataclasses import dataclass

NEUTRAL = 0.5  # used when there is no data, and reported through `trend_coverage`
HAVE, PARTIAL = 0.7, 0.3  # level thresholds for the skills gap


@dataclass(frozen=True)
class Weights:
    skill: float = 0.5
    trend: float = 0.3
    interest: float = 0.2


@dataclass(frozen=True)
class RoleSkill:
    skill_id: str
    importance: float  # 0..1


@dataclass(frozen=True)
class Role:
    role_id: str
    skills: tuple[RoleSkill, ...]
    interest_tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MatchProfile:
    skills: dict[str, float]  # skill_id -> level 0..1 (confirmed by user, M2-03)
    interests: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _RoleScore:
    """Internal result of the scoring engine.

    This is NOT the API contract type; the service maps it to
    ``contracts.matching.RoleMatch`` (which adds label, sdg_targets, meta).
    """

    role_id: str
    score: float
    breakdown: dict[str, float]  # keys: "skill" / "trend" / "interest", each 0..1
    gap: dict[str, list[str]]  # buckets: "have" / "partial" / "missing"
    trend_coverage: float = 1.0  # share of role skill weight that had trend data


def trend_scores(velocities: dict[str, float]) -> dict[str, float]:
    """Percentile rank of each skill's velocity inside one snapshot (0..1, ties averaged).

    Rank-based on purpose: one outlier (for example ai-agents at 0.17) cannot
    squash every other skill to ~0, and the scale does not depend on the scenario.
    """
    items = sorted(velocities.items(), key=lambda kv: kv[1])
    n = len(items)
    out: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        pct = ((i + j) / 2) / (n - 1) if n > 1 else NEUTRAL
        for k in range(i, j + 1):
            out[items[k][0]] = pct
        i = j + 1
    return out


def skill_overlap(profile: MatchProfile, role: Role) -> float:
    total = sum(rs.importance for rs in role.skills)
    if total == 0:
        return 0.0
    have = sum(
        rs.importance * min(max(profile.skills.get(rs.skill_id, 0.0), 0.0), 1.0)
        for rs in role.skills
    )
    return have / total


def role_trend(role: Role, scores: dict[str, float]) -> tuple[float, float]:
    """Importance-weighted trend of the role's skills. Returns (trend, coverage)."""
    total = sum(rs.importance for rs in role.skills)
    if total == 0:
        return NEUTRAL, 0.0
    covered = sum(rs.importance for rs in role.skills if rs.skill_id in scores)
    value = sum(rs.importance * scores.get(rs.skill_id, NEUTRAL) for rs in role.skills) / total
    return value, covered / total


def interest_fit(profile: MatchProfile, role: Role) -> float:
    if not profile.interests:
        return NEUTRAL
    return len(profile.interests & role.interest_tags) / len(profile.interests)


def skills_gap(profile: MatchProfile, role: Role) -> dict[str, list[str]]:
    gap: dict[str, list[str]] = {"have": [], "partial": [], "missing": []}
    for rs in role.skills:
        level = profile.skills.get(rs.skill_id, 0.0)
        bucket = "have" if level >= HAVE else "partial" if level >= PARTIAL else "missing"
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
    return _RoleScore(
        role_id=role.role_id,
        score=w.skill * s + w.trend * t + w.interest * i,
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
) -> list[_RoleScore]:
    """Score and rank roles. Tie-break on role_id for determinism (M2-13)."""
    scores = trend_scores(velocities)
    matches = [score_role(profile, r, scores, w) for r in roles]
    return sorted(matches, key=lambda m: (-m.score, m.role_id))
