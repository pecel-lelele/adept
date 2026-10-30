"""Data access for matching (F4).

Reads shared taxonomy reference data and the saved profile, runs the real scoring engine, and
maps internal `_RoleScore` objects to the API contract type `RoleMatch`.

Missing profiles or skills raise ProfileRequiredError; production never loads personas.
"""

from __future__ import annotations

from dataclasses import replace

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.matching import RoleMatch, ScoreComponent, ScoreImprovement
from app.contracts.pathway import Course
from app.contracts.profile import Skill
from app.core import refdata, seed
from app.core.errors import ProfileRequiredError
from app.features.matching import sdg_weight
from app.features.matching.critical_occupations import badge_for_role
from app.features.matching.gap_port import fetch_skills_gap
from app.features.matching.scoring import (
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    _RoleScore,
    rank_roles,
    skill_credit,
)
from app.features.matching.sdg_port import fetch_role_badges
from app.features.pathway import data as pathway_data
from app.features.profile import service as profile_service
from app.features.sdg import repository as sdg_repository

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
    """Build Role objects from the taxonomy seed files.

    `refdata.rows` shares DB-first reference data with profile and pathways; file-backed
    development picks up edited CSVs without a restart.
    """
    roles_rows = refdata.rows("taxonomy", "roles")
    skill_rows = refdata.rows("taxonomy", "skills")
    link_rows = refdata.rows("taxonomy", "role_skills")
    global _roles_cache  # noqa: PLW0603
    # seed.rows returns the same tuple objects until a file changes, so their ids are the key.
    key = (id(roles_rows), id(skill_rows), id(link_rows))
    if _roles_cache is None or _roles_cache[0] != key:
        _roles_cache = (key, _build_roles(roles_rows, skill_rows, link_rows))
    # Tags are read through the public getter each time so the benchmark sees patched tags.
    return [replace(r, interest_tags=role_interest_tags(r.role_id)) for r in _roles_cache[1]]


_roles_cache: tuple[tuple[int, int, int], tuple[Role, ...]] | None = None


def _build_roles(
    roles_rows: tuple[dict[str, str], ...],
    skill_rows: tuple[dict[str, str], ...],
    link_rows: tuple[dict[str, str], ...],
) -> tuple[Role, ...]:
    _ROLE_LABELS.clear()
    _ROLE_INTEREST_TAGS.clear()
    _SKILL_LABELS.clear()
    for row in roles_rows:
        _ROLE_LABELS[row["id"]] = row["label"]
        _ROLE_INTEREST_TAGS[row["id"]] = frozenset(
            tag.strip() for tag in (row.get("interest_tags") or "").split("|") if tag.strip()
        )
    for row in skill_rows:
        _SKILL_LABELS[row["id"]] = row["label"]
    skills_by_role: dict[str, list[RoleSkill]] = {}
    targets = {r["id"] for r in roles_rows if seed.as_bool(r.get("is_target", "true"))}
    for row in link_rows:
        skills_by_role.setdefault(row["role_id"], []).append(
            RoleSkill(
                skill_id=row["skill_id"],
                importance=float(row["importance"]),
                required_level=int(row.get("required_level") or 1),
            )
        )
    return tuple(
        Role(
            role_id=role_id,
            skills=tuple(skill_list),
            interest_tags=role_interest_tags(role_id),
        )
        for role_id, skill_list in skills_by_role.items()
        if role_id in targets
    )


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

    # Use user's skill level (1-5 scale) directly for required_level comparison
    # Completed learning with accepted evidence (reviewer-confirmed, or a certificate on the
    # provider's verification page) raises a level; self-reported ticks do not (H08).
    from app.features.pathway import service as pathway_service

    skills = {
        skill_id: float(level)
        for skill_id, level in pathway_service.combined_levels(
            user_id, {s.skill_id: s.level for s in profile.skills}
        ).items()
    }
    interests = frozenset(profile.interests)

    return MatchProfile(skills=skills, interests=interests)


def score_components(role_score: _RoleScore, scenario: ScenarioId) -> list[ScoreComponent]:
    """Canonical explanation and values used for display and weighted reranking."""
    bd = role_score.breakdown
    skill_value = bd["skill"]
    trend_value = bd["trend"]
    if skill_value is None or trend_value is None:
        raise ValueError("A scored role must have skill and trend values")

    return [
        ScoreComponent(
            name="skill_overlap",
            weight=_W.skill,
            value=skill_value,
            explanation="Share of required skills weighted by importance.",
        ),
        ScoreComponent(
            name="trend_outlook",
            weight=_W.trend,
            value=trend_value,
            explanation=(
                "Importance-weighted skill trend position: velocity clamped to +/-2, median-scaled "
                f"log-tanh to 0-1, 0.5 = no data ({scenario})."
            ),
        ),
        ScoreComponent(
            name="interest_fit",
            weight=_W.interest,
            value=(bd["interest"] if bd["interest"] is not None else NEUTRAL),
            provided=bd["interest"] is not None,
            explanation=(
                "Jaccard similarity (intersection over union) between your interests and this"
                " role's tags."
                if bd["interest"] is not None
                else "Not provided: you have no saved interests, so a neutral 0.5 is used here."
            ),
        ),
    ]


def _score_to_contract(
    role_score: _RoleScore,
    scenario: ScenarioId,
    meta: RecommendationMeta,
    user_levels: dict[str, int],
    catalogue: list[Course],
) -> RoleMatch:
    """Map a scoring._RoleScore to the API contract RoleMatch."""
    # Ensure labels are populated
    _load_roles()

    role_id = role_score.role_id
    source = pathway_data.taxonomy_source()
    meta = meta.model_copy(
        update={
            "sources": [
                *meta.sources,
                source,
                sdg_repository.un_source(),
                sdg_repository.mapping_source(),
            ]
        }
    )
    # Gap status from unified gap port (pathway.service.skills_gap)
    gap = fetch_skills_gap(user_levels, role_id)

    def _skill_obj(sid: str) -> Skill:
        return Skill(id=sid, label=_SKILL_LABELS.get(sid, sid))

    reqs = pathway_data.requirements(role_id)
    total = sum(r.importance for r in reqs)
    improvements: list[ScoreImprovement] = []
    for req in reqs:
        credit = skill_credit(user_levels.get(req.skill_id, 0), req.required_level)
        if credit >= 1 or total <= 0:
            continue
        courses = [
            c
            for c in catalogue
            if req.skill_id in c.skill_ids
            and c.level >= req.required_level
            and c.format != "subscription"
        ]
        course = min(courses, key=lambda c: (c.cost_myr, c.hours, c.id), default=None)
        improvements.append(
            ScoreImprovement(
                skill=req.skill_id,
                label=_SKILL_LABELS.get(req.skill_id, req.skill_id),
                score_gain=_W.skill * req.importance / total * (1 - credit),
                course_id=course.id if course else None,
                course_title=course.title if course else None,
                course_url=course.url if course else None,
            )
        )
        if course and course.source and course.source not in meta.sources:
            meta = meta.model_copy(update={"sources": [*meta.sources, course.source]})
    improvements.sort(key=lambda item: (-item.score_gain, item.skill))

    return RoleMatch(
        role_id=role_id,
        label=_ROLE_LABELS.get(role_id, role_id),
        score=role_score.score,
        components=score_components(role_score, scenario),
        missing_skills=[_skill_obj(s) for s in gap.get("missing", [])],
        partial_skills=[_skill_obj(s) for s in gap.get("partial", [])],
        sdg_targets=fetch_role_badges(role_id),
        critical_occupation=badge_for_role(role_id, scenario),
        improvements=improvements,
        profile_note="add_skills" if not user_levels else None,
        trend_coverage=round(role_score.trend_coverage, 4),
        meta=meta,
    )


def _ranked_scores(
    profile: MatchProfile,
    roles: list[Role],
    velocities: dict[str, float],
    reference_velocities: dict[str, float] | None,
    scenario: ScenarioId,
    impact: dict[str, float],
    weight: float,
) -> list[tuple[str, float]]:
    ranked = rank_roles(profile, roles, velocities, _W, reference_velocities=reference_velocities)
    if weight <= 0:
        return [(r.role_id, r.score) for r in ranked]
    return sorted(
        [
            (
                r.role_id,
                sdg_weight.component_score(
                    sdg_weight.blend_components(
                        score_components(r, scenario), impact.get(r.role_id, 0.0), weight
                    )
                ),
            )
            for r in ranked
        ],
        key=lambda item: (-item[1], item[0]),
    )


def list_matches(
    user_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    meta: RecommendationMeta,
    reference_velocities: dict[str, float] | None = None,
    *,
    sdg_weight_value: float = 0.0,
) -> list[RoleMatch]:
    """Rank one saved profile, including same-snapshot comparisons and skill counterfactuals."""
    profile = _load_profile(user_id)
    roles = _load_roles()
    ranked = rank_roles(profile, roles, velocities, _W, reference_velocities=reference_velocities)
    user_levels = {k: int(round(v)) for k, v in profile.skills.items()}
    catalogue = pathway_data.catalogue()
    matches = [_score_to_contract(r, scenario, meta, user_levels, catalogue) for r in ranked]
    links = (
        {r.role_id: sdg_weight.default_links(r.role_id) for r in roles}
        if sdg_weight_value > 0
        else {}
    )
    impact = sdg_weight.sdg_impact(links, lambda rid: links[rid])
    matches = sdg_weight.apply(
        matches,
        impact,
        sdg_weight_value,
        {rid: sdg_weight.review_note(found) for rid, found in links.items()},
    )
    other_scenario: ScenarioId = "fast" if scenario == "moderate" else "moderate"
    other = (
        {
            rid: (index, score)
            for index, (rid, score) in enumerate(
                _ranked_scores(
                    profile,
                    roles,
                    reference_velocities,
                    velocities,
                    other_scenario,
                    impact,
                    sdg_weight_value,
                ),
                1,
            )
        }
        if reference_velocities is not None
        else {}
    )
    # Many roles share a required skill/level: compute each changed profile just once.
    counterfactuals: dict[tuple[str, int], dict[str, int]] = {}
    role_by_id = {r.role_id: r for r in roles}
    out: list[RoleMatch] = []
    for index, match in enumerate(matches, 1):
        improvements = list(match.improvements)
        for i, item in enumerate(improvements[:3]):
            req = next(r for r in role_by_id[match.role_id].skills if r.skill_id == item.skill)
            key = (item.skill, req.required_level)
            if key not in counterfactuals:
                raised = replace(
                    profile, skills={**profile.skills, item.skill: float(req.required_level)}
                )
                counterfactuals[key] = {
                    rid: pos
                    for pos, (rid, _) in enumerate(
                        _ranked_scores(
                            raised,
                            roles,
                            velocities,
                            reference_velocities,
                            scenario,
                            impact,
                            sdg_weight_value,
                        ),
                        1,
                    )
                }
            improvements[i] = item.model_copy(
                update={"new_rank": counterfactuals[key][match.role_id]}
            )
        alternative = other.get(match.role_id)
        out.append(
            match.model_copy(
                update={
                    "rank": index,
                    "other_scenario": other_scenario if alternative else None,
                    "other_rank": alternative[0] if alternative else None,
                    "other_score": alternative[1] if alternative else None,
                    "improvements": improvements,
                }
            )
        )
    return out


def get_match(
    user_id: str,
    role_id: str,
    scenario: ScenarioId,
    velocities: dict[str, float],
    meta: RecommendationMeta,
    reference_velocities: dict[str, float] | None = None,
    *,
    sdg_weight_value: float = 0.0,
) -> RoleMatch | None:
    """Use the full production ranking so list/detail counterfactual ranks agree."""
    return next(
        (
            m
            for m in list_matches(
                user_id,
                scenario,
                velocities,
                meta,
                reference_velocities,
                sdg_weight_value=sdg_weight_value,
            )
            if m.role_id == role_id
        ),
        None,
    )
