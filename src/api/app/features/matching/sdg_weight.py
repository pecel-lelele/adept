"""SDG-weighted ranking (F4, good-to-have "SDG slider").

The learner chooses how much the UN Goals should count, lambda in [0, 1]. Each role gets an SDG
impact value from its SDG links (draft and reviewed alike, and the explanation says how many
are reviewed): a direct link counts 1, an enabling link 0.5, summed
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


def review_note(links: Iterable[SdgLink]) -> str:
    """How many of the links behind the impact value a person has reviewed."""
    items = list(links)
    reviewed = sum(1 for link in items if link.reviewed)
    if not items:
        return "This role has no SDG links yet."
    if reviewed == len(items):
        return f"All {len(items)} links were reviewed by a person."
    return (
        f"{reviewed} of {len(items)} links were reviewed by a person; the rest are draft "
        "mappings, marked as drafts on the Impact page."
    )


def apply(
    matches: list[RoleMatch],
    impact: dict[str, float],
    weight: float,
    notes: dict[str, str] | None = None,
) -> list[RoleMatch]:
    """Blend SDG impact into each score and re-rank (stable tie-break on role_id).

    ``notes`` (role -> text) is appended to the explanation, e.g. how many links are drafts.
    """
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
                    "Strength of this role's links to the UN Sustainable Development Goals "
                    "(direct links count fully, enabling links half), relative to the strongest "
                    "role. " + (notes or {}).get(m.role_id, "")
                ).strip(),
            )
        )
        score = min(1.0, sum(c.weight * c.value for c in parts))
        skill_weight = next((c.weight for c in parts if c.name == "skill_overlap"), 0.0)
        old_skill_weight = next((c.weight for c in m.components if c.name == "skill_overlap"), 0.0)
        improvements = (
            [
                item.model_copy(
                    update={"score_gain": item.score_gain * skill_weight / old_skill_weight}
                )
                for item in m.improvements
            ]
            if old_skill_weight
            else []
        )
        out.append(
            m.model_copy(
                update={
                    "components": parts,
                    "score": round(score, 6),
                    "improvements": improvements,
                }
            )
        )
    return sorted(out, key=lambda m: (-m.score, m.role_id))


def default_links(role_id: str) -> list[SdgLink]:
    from app.features.sdg import repository as sdg_repository

    return sdg_repository.role_links(role_id)
