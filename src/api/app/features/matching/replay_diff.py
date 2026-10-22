"""Trend replay with reasons (F4/F2, good-to-have "what changed and why").

Ranks the same profile on two snapshot dates (``replay.replay``) and, for every role, names
the skills that moved its trend part most: the change in each required skill's velocity times
its importance in the role. Those are the "why" behind a role moving up or down.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.features.matching.replay import RoleMovement, replay
from app.features.matching.scoring import MatchProfile, Role, Weights


@dataclass(frozen=True)
class Driver:
    skill_id: str
    velocity_before: float
    velocity_after: float
    effect: float  # (after - before) * importance; sign = direction of the push


def drivers(
    role: Role, before: dict[str, float], after: dict[str, float], top: int = 2
) -> list[Driver]:
    """The required skills whose trend moved this role most between the two snapshots."""
    found = [
        Driver(
            skill_id=rs.skill_id,
            velocity_before=round(before.get(rs.skill_id, 0.0), 4),
            velocity_after=round(after.get(rs.skill_id, 0.0), 4),
            effect=round(
                (after.get(rs.skill_id, 0.0) - before.get(rs.skill_id, 0.0)) * rs.importance, 4
            ),
        )
        for rs in role.skills
        if rs.skill_id in before or rs.skill_id in after
    ]
    found = [d for d in found if abs(d.effect) > 1e-6]
    return sorted(found, key=lambda d: (-abs(d.effect), d.skill_id))[:top]


def compare(
    profile: MatchProfile,
    roles: list[Role],
    before: dict[str, float],
    after: dict[str, float],
    w: Weights,
) -> list[tuple[RoleMovement, list[Driver]]]:
    by_id = {r.role_id: r for r in roles}
    return [
        (m, drivers(by_id[m.role_id], before, after))
        for m in replay(profile, roles, before, after, w)
    ]
