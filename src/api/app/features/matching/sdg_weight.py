"""SDG-weighted ranking (F4, good-to-have "SDG slider").

The learner chooses how much the UN Goals should count, lambda in [0, 1]. Each role gets an SDG
impact value from its reviewed SDG links: a direct link counts 1, an enabling link 0.5, summed
and divided by the strongest role's total so the value is 0..1. The existing score parts keep
their relative weights scaled by (1 - lambda) and SDG impact is added with weight lambda, so the
score stays a weighted sum shown part by part. lambda = 0 leaves the ranking unchanged.

Pure functions; the link lookup is passed in so tests need no SDG data.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from app.contracts.matching import RoleMatch, ScoreComponent
from app.contracts.sdg import SdgLink

LinkFn = Callable[[str], list[SdgLink]]
STRENGTH = {"direct": 1.0, "enabling": 0.5}


def link_weight(links: Iterable[SdgLink]) -> float:
    return sum(STRENGTH.get(link.strength, 0.5) for link in links)


def sdg_impact(role_ids: Iterable[str], links_for: LinkFn) -> dict[str, float]:
    """Role -> SDG impact 0..1, relative to the role with the strongest SDG links."""
    raw = {rid: link_weight(links_for(rid)) for rid in role_ids}
    top = max(raw.values(), default=0.0)
    if top <= 0:
        return {rid: 0.0 for rid in raw}
    return {rid: round(value / top, 4) for rid, value in raw.items()}


def apply(matches: list[RoleMatch], impact: dict[str, float], weight: float) -> list[RoleMatch]:
    """Blend SDG impact into each score and re-rank (stable tie-break on role_id)."""
    if weight <= 0:
        return matches
    weight = min(1.0, weight)
    out: list[RoleMatch] = []
    for m in matches:
        parts = [
            c.model_copy(update={"weight": round(c.weight * (1 - weight), 4)}) for c in m.components
        ]
        parts.append(
            ScoreComponent(
                name="sdg_impact",
                weight=round(weight, 4),
                value=impact.get(m.role_id, 0.0),
                explanation=(
                    "Strength of this role's reviewed links to the UN Sustainable Development "
                    "Goals (direct links count fully, enabling links half), relative to the "
                    "strongest role."
                ),
            )
        )
        score = min(1.0, sum(c.weight * c.value for c in parts))
        out.append(m.model_copy(update={"components": parts, "score": round(score, 6)}))
    return sorted(out, key=lambda m: (-m.score, m.role_id))


def default_links(role_id: str) -> list[SdgLink]:
    from app.features.sdg import repository as sdg_repository

    return sdg_repository.role_links(role_id)
