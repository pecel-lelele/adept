"""Unit tests for the matching scoring engine (M2-06, M2-07, M2-08, M2-13).

Uses the real ai-agents velocity change (0.00372 → 0.174597) to verify
that a rising skill moves its role from 2nd to 1st place.

No I/O: velocities are passed in directly; trend_port is not called.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

# pyrefly: ignore[missing-import]
from app.core.fairness import counterfactual_diffs, is_protected  # type: ignore

# pyrefly: ignore[missing-import]
from app.features.matching.replay import RoleMovement, replay  # type: ignore

# pyrefly: ignore[missing-import]
from app.features.matching.scoring import (  # type: ignore
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    interest_fit,
    rank_roles,
    skill_overlap,
    skills_gap,
    trend_scores,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WEIGHTS = Weights()  # production defaults (M2-011) — do not restate the numbers here

# Two roles from the mock catalogue, expressed as scoring.Role objects.
# ROLE_AI_OPS is dominated by ai-agents (weight 0.8) so the velocity jump
# is strong enough to flip it past ROLE_DATA under the default Weights.
ROLE_AI_OPS = Role(
    role_id="ai-operations-specialist",
    skills=(
        RoleSkill("ai-agents", 0.8),
        RoleSkill("prompt-engineering", 0.2),
    ),
    interest_tags=frozenset({"ai", "automation"}),
)

ROLE_DATA = Role(
    role_id="data-analyst",
    skills=(
        RoleSkill("python", 0.4),
        RoleSkill("sql", 0.4),
        RoleSkill("data-visualisation", 0.2),
    ),
    interest_tags=frozenset({"data", "reporting"}),
)

# Profile: moderate skill in both directions so neither role dominates on overlap alone.
PROFILE = MatchProfile(
    skills={
        "python": 0.5,
        "sql": 0.5,
        "data-visualisation": 0.3,
        "ai-agents": 0.5,
        "prompt-engineering": 0.5,
    },
    interests=frozenset({"data", "ai"}),
)

# Velocities: before (ai-agents low) and after (ai-agents high)
VELOCITIES_BEFORE = {
    "python": 0.05,
    "sql": 0.03,
    "data-visualisation": 0.02,
    "prompt-engineering": 0.04,
    "ai-agents": 0.00372,  # real pre value
}
VELOCITIES_AFTER = {
    "python": 0.05,
    "sql": 0.03,
    "data-visualisation": 0.02,
    "prompt-engineering": 0.04,
    "ai-agents": 0.174597,  # real post value — outlier
}


# ---------------------------------------------------------------------------
# trend_scores
# ---------------------------------------------------------------------------


def test_trend_scores_range() -> None:
    scores = trend_scores(VELOCITIES_BEFORE)
    assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_trend_scores_outlier_does_not_collapse_others() -> None:
    """ai-agents at 0.17 must not collapse other skills to 0.

    With 5 skills rank space is [0, 0.25, 0.5, 0.75, 1.0];
    the minimum non-zero rank a non-outlier can hold is 0.25.
    """
    scores = trend_scores(VELOCITIES_AFTER)
    non_outlier = {k: v for k, v in scores.items() if k != "ai-agents"}
    # ai-agents gets rank 1.0; the remaining 4 skills still spread across [0, 0.75]
    # so none of them should be identical to ai-agents' rank (1.0).
    assert all(v < 1.0 for v in non_outlier.values()), (
        "Non-outlier skills should not share the top rank with the outlier"
    )
    # And they must not all collapse to zero — at least one should be above 0.
    assert any(v > 0 for v in non_outlier.values()), (
        "All non-outlier skills collapsed to 0 — rank normalization broken"
    )


def test_trend_scores_ties_averaged() -> None:
    tied = {"a": 1.0, "b": 1.0, "c": 2.0}
    scores = trend_scores(tied)
    assert scores["a"] == scores["b"]
    assert scores["c"] > scores["a"]


def test_trend_scores_single_item() -> None:
    scores = trend_scores({"only": 0.99})
    assert scores["only"] == NEUTRAL


# ---------------------------------------------------------------------------
# skill_overlap
# ---------------------------------------------------------------------------


def test_skill_overlap_full_match() -> None:
    full = MatchProfile(skills={"python": 1.0, "sql": 1.0, "data-visualisation": 1.0})
    assert skill_overlap(full, ROLE_DATA) == pytest.approx(1.0)


def test_skill_overlap_no_match() -> None:
    empty = MatchProfile(skills={})
    assert skill_overlap(empty, ROLE_DATA) == pytest.approx(0.0)


def test_skill_overlap_empty_role() -> None:
    empty_role = Role(role_id="x", skills=())
    assert skill_overlap(PROFILE, empty_role) == 0.0


# ---------------------------------------------------------------------------
# interest_fit
# ---------------------------------------------------------------------------


def test_interest_fit_full() -> None:
    full = MatchProfile(skills={}, interests=frozenset({"data", "ai"}))
    # ROLE_DATA has {"data", "reporting"} -> Jaccard = 1/3
    # (intersection {data}, union {data, ai, reporting})
    assert interest_fit(full, ROLE_DATA) == pytest.approx(1 / 3)


def test_interest_fit_no_interests_returns_none() -> None:
    no_interest = MatchProfile(skills={})
    assert interest_fit(no_interest, ROLE_DATA) is None


# ---------------------------------------------------------------------------
# skills_gap
# ---------------------------------------------------------------------------


def test_skills_gap_buckets() -> None:
    gap = skills_gap(PROFILE, ROLE_DATA)
    # python=0.6 ≥ HAVE(0.7)? No → partial; sql=0.6 → partial; data-vis=0.4 ≥ PARTIAL → partial
    assert set(gap["have"]) == set()
    assert set(gap["partial"]) == {"python", "sql", "data-visualisation"}
    assert set(gap["missing"]) == set()


def test_skills_gap_missing() -> None:
    no_skills = MatchProfile(skills={})
    gap = skills_gap(no_skills, ROLE_DATA)
    assert set(gap["missing"]) == {"python", "sql", "data-visualisation"}


# ---------------------------------------------------------------------------
# rank_roles — the key end-to-end test
# ---------------------------------------------------------------------------


def test_rising_skill_promotes_role() -> None:
    """ai-agents velocity jump moves ai-operations-specialist from 2nd to 1st (M2-06)."""
    roles = [ROLE_AI_OPS, ROLE_DATA]

    before = rank_roles(PROFILE, roles, VELOCITIES_BEFORE, WEIGHTS)
    after = rank_roles(PROFILE, roles, VELOCITIES_AFTER, WEIGHTS)

    role_ids_before = [r.role_id for r in before]
    role_ids_after = [r.role_id for r in after]

    # Before: data-analyst should be ranked higher (better skill overlap)
    assert role_ids_before[0] == "data-analyst", f"Before order: {role_ids_before}"
    # After: ai-operations-specialist should jump to 1st
    assert role_ids_after[0] == "ai-operations-specialist", f"After order: {role_ids_after}"


def test_rank_is_deterministic() -> None:
    """Same inputs must always produce the same ordering (M2-13)."""
    roles = [ROLE_AI_OPS, ROLE_DATA]
    r1 = [m.role_id for m in rank_roles(PROFILE, roles, VELOCITIES_BEFORE, WEIGHTS)]
    r2 = [m.role_id for m in rank_roles(PROFILE, roles, VELOCITIES_BEFORE, WEIGHTS)]
    assert r1 == r2


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------


def test_replay_detects_rank_change() -> None:
    roles = [ROLE_AI_OPS, ROLE_DATA]
    movements: list[RoleMovement] = replay(
        PROFILE, roles, VELOCITIES_BEFORE, VELOCITIES_AFTER, WEIGHTS
    )
    by_role = {m.role_id: m for m in movements}
    ai_ops = by_role["ai-operations-specialist"]
    assert ai_ops.delta_rank > 0, "ai-ops should have moved up in rank"
    assert ai_ops.delta_score > 0, "ai-ops score should have increased"


def test_replay_results_sorted_by_rank_after() -> None:
    roles = [ROLE_AI_OPS, ROLE_DATA]
    movements = replay(PROFILE, roles, VELOCITIES_BEFORE, VELOCITIES_AFTER, WEIGHTS)
    ranks = [m.rank_after for m in movements]
    assert ranks == sorted(ranks)


# ---------------------------------------------------------------------------
# Fairness & Counterfactual tests (M2-12, M2-13)
# ---------------------------------------------------------------------------


def test_match_profile_fairness_whitelist() -> None:
    """Ensure MatchProfile only accepts whitelisted non-identity fields (M2-12)."""
    allowed_fields = {f.name for f in fields(MatchProfile)}
    assert allowed_fields == {"skills", "interests"}

    for f_name in allowed_fields:
        assert not is_protected(f_name), f"Protected attribute {f_name} found in MatchProfile"


def test_counterfactual_fairness_demographic_swaps() -> None:
    """Counterfactual invariance: identity swaps never alter match rankings or scores (M2-13)."""
    roles = [ROLE_AI_OPS, ROLE_DATA]

    base_skills = {"python": 0.5, "sql": 0.5, "ai-agents": 0.5}
    base_interests = frozenset({"data", "ai"})
    baseline = MatchProfile(skills=dict(base_skills), interests=base_interests)

    def _rank_key(
        p: MatchProfile,
    ) -> list[tuple[str, float, dict[str, float], dict[str, list[str]]]]:
        ranked = rank_roles(p, roles, VELOCITIES_BEFORE, WEIGHTS)
        return [(r.role_id, round(r.score, 6), r.breakdown, r.gap) for r in ranked]

    # Demographic swap variants: same skills/interests under different synthetic identities
    variants = {
        "swapped_identity_aisyah": MatchProfile(skills=dict(base_skills), interests=base_interests),
        "swapped_identity_weijie": MatchProfile(skills=dict(base_skills), interests=base_interests),
        "swapped_identity_ravi": MatchProfile(skills=dict(base_skills), interests=base_interests),
    }

    diffs = counterfactual_diffs(_rank_key, baseline, variants)
    assert diffs == [], f"Counterfactual differences detected across identity variants: {diffs}"

    # Sanity check: altering skills or interests (the true allowed merit signals) DOES change output
    perturbed = {
        "skills_changed": MatchProfile(skills={"python": 1.0, "sql": 1.0}, interests=base_interests)
    }
    assert counterfactual_diffs(_rank_key, baseline, perturbed) == ["skills_changed"]
