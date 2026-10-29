"""Bounded catalogue proposals for an explicitly submitted skill-bank search.

Each tier contributes at most one candidate; deduplication can only reduce the union.
Semantic selection delegates to the existing top-1 0.80/0.015 decision rule.
"""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from app.contracts.profile import SkillResolutionCandidate, SkillResolutionResponse
from app.core.llm.validator import validate_ids
from app.core.security.sanitize import sanitize_text
from app.features.profile import cv_parser, skill_match
from app.features.profile.service import TAXONOMY_META

FUZZY_MIN_SIMILARITY = 0.83
FUZZY_MIN_MARGIN = 0.05
MIN_QUERY_ALNUM = 4


def normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def fuzzy_scores(
    query: str, taxonomy: dict[str, cv_parser.TaxonomySkill]
) -> list[tuple[str, float]]:
    """Score each distinct skill by its best label/alias, retaining the top two."""
    query = normalise(query)
    scored = [
        (
            sid,
            max(
                SequenceMatcher(None, query, normalise(text), autojunk=False).ratio()
                for text in (skill.label, *skill.aliases)
                if text
            ),
        )
        for sid, skill in taxonomy.items()
    ]
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:2]


def fuzzy_candidate(
    query: str, taxonomy: dict[str, cv_parser.TaxonomySkill]
) -> SkillResolutionCandidate | None:
    if sum(c.isalnum() for c in normalise(query)) < MIN_QUERY_ALNUM:
        return None
    ranked = fuzzy_scores(query, taxonomy)
    if not ranked:
        return None
    sid, score = ranked[0]
    runner_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if score < FUZZY_MIN_SIMILARITY or score - runner_score < FUZZY_MIN_MARGIN:
        return None
    return SkillResolutionCandidate(
        skill_id=sid, label=taxonomy[sid].label, method="fuzzy", score=score
    )


def resolve(query: str) -> SkillResolutionResponse:
    query = normalise(sanitize_text(query, max_length=80, allow_newlines=False, field="query"))
    taxonomy = cv_parser._load_taxonomy()  # noqa: SLF001 - same canonical catalogue as CV intake
    candidates: dict[str, SkillResolutionCandidate] = {}
    exact = [
        sid
        for sid, skill in taxonomy.items()
        if query in {normalise(text) for text in (sid, skill.label, *skill.aliases)}
    ]
    if len(exact) == 1:
        sid = exact[0]
        candidates[sid] = SkillResolutionCandidate(
            skill_id=sid, label=taxonomy[sid].label, method="alias", score=1.0
        )
    fuzzy = fuzzy_candidate(query, taxonomy)
    if fuzzy:
        candidates.setdefault(fuzzy.skill_id, fuzzy)
    ranked = fuzzy_scores(query, taxonomy)
    fuzzy_too_close = (
        len(ranked) > 1
        and ranked[0][1] >= FUZZY_MIN_SIMILARITY
        and ranked[0][1] - ranked[1][1] < FUZZY_MIN_MARGIN
    )
    # An exact catalogue alias needs no model call. Short/ambiguous exact searches never
    # leave the API. suggest() uses only an already prepared index and returns top-1.
    if not exact and not fuzzy_too_close and sum(c.isalnum() for c in query) >= MIN_QUERY_ALNUM:
        for suggestion in skill_match.suggest([query])[:1]:
            if suggestion.skill_id not in taxonomy:
                continue
            validate_ids([suggestion.skill_id], taxonomy)
            candidates.setdefault(
                suggestion.skill_id,
                SkillResolutionCandidate(
                    skill_id=suggestion.skill_id,
                    label=taxonomy[suggestion.skill_id].label,
                    method="semantic",
                    score=suggestion.similarity,
                ),
            )
    return SkillResolutionResponse(
        query=query, candidates=list(candidates.values()), meta=TAXONOMY_META
    )
