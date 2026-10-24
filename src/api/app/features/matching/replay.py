"""Snapshot replay: rank the same profile on two dates, show role movement (M2-08).

Pure function, no I/O.  The caller (service or test) supplies both velocity dicts.
"""

from __future__ import annotations

from dataclasses import dataclass

# pyrefly: ignore[missing-import]
from app.features.matching.scoring import MatchProfile, Role, Weights, rank_roles


@dataclass(frozen=True)
class RoleMovement:
    role_id: str
    rank_before: int  # 1-indexed
    rank_after: int  # 1-indexed
    score_before: float
    score_after: float

    @property
    def delta_rank(self) -> int:
        """Positive = moved up in ranking (improved)."""
        return self.rank_before - self.rank_after

    @property
    def delta_score(self) -> float:
        return round(self.score_after - self.score_before, 6)


_DEFAULT_WEIGHTS = Weights()  # module-level singleton — avoids B008


def replay(
    profile: MatchProfile,
    roles: list[Role],
    velocities_before: dict[str, float],
    velocities_after: dict[str, float],
    w: Weights = _DEFAULT_WEIGHTS,
) -> list[RoleMovement]:
    """Return role movements sorted by ``rank_after`` (best match first)."""
    before = {
        r.role_id: (i + 1, r.score)
        for i, r in enumerate(rank_roles(profile, roles, velocities_before, w))
    }
    after_ranked = rank_roles(profile, roles, velocities_after, w)
    movements = []
    for i, r in enumerate(after_ranked):
        rank_b, score_b = before[r.role_id]
        movements.append(
            RoleMovement(
                role_id=r.role_id,
                rank_before=rank_b,
                rank_after=i + 1,
                score_before=round(score_b, 6),
                score_after=round(r.score, 6),
            )
        )
    return movements
