"""How close a learner is to real openings, now and after their plan (pure functions).

An ad names some catalogue skills. A skill counts as met when the learner's level reaches the
role's required level for it (level 2, working knowledge, for skills outside the role's
requirements). The plan meets it when a plan step reaches that level. An opening is "within
reach" when at least READY_SHARE of the skills its ad names are met. Ads naming fewer than two
catalogue skills are not rated: one keyword is too little to judge from.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

READY_SHARE = 0.6
DEFAULT_LEVEL = 2
MIN_RATED_SKILLS = 2


def status(
    skill_id: str,
    have: Mapping[str, int] | None,
    plan: Mapping[str, int],
    required: Mapping[str, int],
) -> str:
    if have is None:
        return "not_rated"
    need = required.get(skill_id, DEFAULT_LEVEL)
    if have.get(skill_id, 0) >= need:
        return "have"
    if plan.get(skill_id, 0) >= need:
        return "in_plan"
    return "missing"


def shares(statuses: Sequence[str]) -> tuple[float | None, float | None]:
    """(met now, met after the plan) as shares of the ad's skills; None when not rateable."""
    rated = [s for s in statuses if s != "not_rated"]
    if len(rated) < MIN_RATED_SKILLS:
        return None, None
    now = sum(s == "have" for s in rated) / len(rated)
    after = sum(s in ("have", "in_plan") for s in rated) / len(rated)
    return round(now, 3), round(after, 3)


def within_reach(share: float | None) -> bool:
    return share is not None and share >= READY_SHARE


def demand(skill_lists: Iterable[Sequence[str]], top: int = 8) -> list[tuple[str, int]]:
    """Skills named most often across ads, ties broken by id for a stable order."""
    counts: Counter[str] = Counter()
    for skills in skill_lists:
        counts.update(set(skills))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
