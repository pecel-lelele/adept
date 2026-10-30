"""Trend replay with reasons (F4/F2, good-to-have "what changed and why").

Ranks the same profile on two snapshot dates (``replay.replay``) and, for every role, names
the required skills that moved its score most. The scorer does not use raw velocity: it uses
each skill's position on the shared min-max scale (``scoring.trend_scores``).
So a driver's effect is the change in that position times the skill's share of the role's
importance times the trend weight: exactly how many score points that skill added or removed.
Each dated snapshot supplies one range shared by both of its scenarios.

An optional UN Goals weight (``sdg_weight``) blends each role's SDG impact into both scores
the same way as the matches list, so replay explains the ranking the learner selected.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.features.matching.replay import RoleMovement, replay
from app.features.matching.scoring import NEUTRAL, MatchProfile, Role, Weights, trend_scores


@dataclass(frozen=True)
class Driver:
    skill_id: str
    velocity_before: float
    velocity_after: float
    position_before: float  # normalized velocity 0..1 in the earlier snapshot
    position_after: float  # normalized velocity 0..1 in the later snapshot
    effect: float  # score points this skill moved the role; sign = direction of the push


def drivers(
    role: Role,
    before: dict[str, float],
    after: dict[str, float],
    top: int = 2,
    *,
    w: Weights | None = None,
    scale: float = 1.0,
    pos_before: dict[str, float] | None = None,
    pos_after: dict[str, float] | None = None,
) -> list[Driver]:
    """The required skills whose shared-scale velocity moved this role's score most.

    ``scale`` shrinks the effect when the UN Goals weight takes part of the score.
    ``pos_before`` / ``pos_after`` may be passed in to avoid re-ranking per role.
    """
    weights = w or Weights()
    pb = pos_before if pos_before is not None else trend_scores(before)
    pa = pos_after if pos_after is not None else trend_scores(after)
    total = sum(rs.importance for rs in role.skills)
    if total == 0:
        return []
    found = []
    for rs in role.skills:
        if rs.skill_id not in before and rs.skill_id not in after:
            continue
        p0 = pb.get(rs.skill_id, NEUTRAL)
        p1 = pa.get(rs.skill_id, NEUTRAL)
        effect = (p1 - p0) * rs.importance / total * weights.trend * scale
        found.append(
            Driver(
                skill_id=rs.skill_id,
                velocity_before=round(before.get(rs.skill_id, 0.0), 4),
                velocity_after=round(after.get(rs.skill_id, 0.0), 4),
                position_before=round(p0, 4),
                position_after=round(p1, 4),
                effect=round(effect, 4),
            )
        )
    found = [d for d in found if abs(d.effect) > 1e-6]
    return sorted(found, key=lambda d: (-abs(d.effect), d.skill_id))[:top]


def _blend(
    movements: list[RoleMovement], impact: dict[str, float], weight: float
) -> list[RoleMovement]:
    """Re-rank both dates with score' = (1 - weight) * score + weight * SDG impact."""
    if weight <= 0:
        return movements

    def mix(role_id: str, score: float) -> float:
        return round((1 - weight) * score + weight * impact.get(role_id, 0.0), 6)

    before = {m.role_id: mix(m.role_id, m.score_before) for m in movements}
    after = {m.role_id: mix(m.role_id, m.score_after) for m in movements}

    def rank(scores: dict[str, float]) -> dict[str, int]:
        order = sorted(scores, key=lambda rid: (-scores[rid], rid))
        return {rid: i + 1 for i, rid in enumerate(order)}

    rank_b, rank_a = rank(before), rank(after)
    out = [
        RoleMovement(
            role_id=m.role_id,
            rank_before=rank_b[m.role_id],
            rank_after=rank_a[m.role_id],
            score_before=before[m.role_id],
            score_after=after[m.role_id],
        )
        for m in movements
    ]
    return sorted(out, key=lambda m: m.rank_after)


def compare(
    profile: MatchProfile,
    roles: list[Role],
    before: dict[str, float],
    after: dict[str, float],
    w: Weights,
    *,
    impact: dict[str, float] | None = None,
    sdg_weight: float = 0.0,
    reference_before: dict[str, float] | None = None,
    reference_after: dict[str, float] | None = None,
) -> list[tuple[RoleMovement, list[Driver]]]:
    by_id = {r.role_id: r for r in roles}
    weight = min(1.0, max(0.0, sdg_weight)) if impact is not None else 0.0
    movements = _blend(
        replay(
            profile,
            roles,
            before,
            after,
            w,
            reference_before=reference_before,
            reference_after=reference_after,
        ),
        impact or {},
        weight,
    )
    pb, pa = trend_scores(before, reference_before), trend_scores(after, reference_after)
    return [
        (
            m,
            drivers(
                by_id[m.role_id], before, after, w=w, scale=1 - weight, pos_before=pb, pos_after=pa
            ),
        )
        for m in movements
    ]
