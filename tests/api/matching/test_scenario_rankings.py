import pytest
from harness.fixtures import PROFILES

from app.core.auth import CurrentUser
from app.features.matching import service
from app.features.matching.scoring import (
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    rank_roles,
    trend_scores,
)
from app.features.trends import service as trends_service


@pytest.mark.parametrize("user_id", list(PROFILES))
def test_every_demo_profile_has_a_role_score_change_over_half_a_point(user_id: str) -> None:
    user = CurrentUser(user_id, "Synthetic learner", "learner")
    moderate = service.list_matches(user, "moderate").matches
    fast = service.list_matches(user, "fast").matches
    before = {match.role_id: match.score for match in moderate}
    after = {match.role_id: match.score for match in fast}
    assert any(abs(before[role] - after[role]) > 0.005 for role in before), user_id


def test_fast_changes_top_five_scores_on_the_latest_snapshot() -> None:
    """Scenario signals affect leading scores; profile score gaps need not allow a rank flip.

    The synthetic near-tie below independently proves the production ranker can flip.
    """
    changed = []
    for user_id in PROFILES:
        user = CurrentUser(user_id, "Synthetic learner", "learner")
        moderate = service.list_matches(user, "moderate").matches
        fast = service.list_matches(user, "fast").matches
        fast_scores = {m.role_id: m.score for m in fast}
        if any(abs(m.score - fast_scores[m.role_id]) > 0.005 for m in moderate[:5]):
            changed.append(user_id)
        for matches in (moderate, fast):
            assert matches == sorted(matches, key=lambda m: (-m.score, m.role_id))
    assert changed, "Fast left every demo persona's top-five scores within half a point"


def test_fast_never_lowers_a_rising_skill_on_the_latest_snapshot() -> None:
    """Monotonic: on the shared scale Fast >= Moderate for every rising skill, <= for declining."""
    snap = trends_service.get_snapshot(None, "moderate")
    moderate = {i.skill_id: i.velocity_moderate for i in snap.items}
    fast = {i.skill_id: i.velocity_fast for i in snap.items}
    m, f = trend_scores(moderate, fast), trend_scores(fast, moderate)
    for skill, v in moderate.items():
        if v > 0 and fast[skill] >= min(v, 2.0):
            assert f[skill] >= m[skill] - 1e-12, skill
        if v < 0 and fast[skill] <= max(v, -2.0):
            assert f[skill] <= m[skill] + 1e-12, skill
    rising = [s for s, v in moderate.items() if v > 0.05]
    assert rising and all(f[s] >= m[s] - 1e-12 for s in rising)


def test_trend_positions_are_not_collapsed_on_the_latest_snapshot() -> None:
    """Before N1, 75% of skills normalised into 0.576-0.578; the bulk must now spread out."""
    snap = trends_service.get_snapshot(None, "moderate")
    moderate = {i.skill_id: i.velocity_moderate for i in snap.items}
    fast = {i.skill_id: i.velocity_fast for i in snap.items}
    values = sorted(trend_scores(moderate, fast).values())
    q1, q3 = values[len(values) // 4], values[3 * len(values) // 4]
    assert q3 - q1 > 0.1


def test_trend_scale_is_shared_between_both_scenarios() -> None:
    before = {"same": 0.05, "moving": 0.01}
    after = {"same": 0.05, "moving": 0.1}
    moderate = trend_scores(before, after)
    fast = trend_scores(after, before)
    assert moderate["same"] == fast["same"]
    assert moderate["moving"] < fast["moving"]
    spread = trend_scores({"declining": -0.1, "neutral": 0, "rising": 0.1})
    assert spread["declining"] < spread["neutral"] == NEUTRAL < spread["rising"]
    assert spread["declining"] == pytest.approx(1 - spread["rising"])


def test_near_tie_flips_with_fast_velocity_before_shared_normalization() -> None:
    """Fast amplifies only role B's rising skill; a near skill tie in A's favour then flips."""
    moderate = {"synthetic-a": 0.1, "synthetic-b": 0.2}
    fast = {"synthetic-a": 0.1, "synthetic-b": 0.4}
    weights = Weights()
    m, f = trend_scores(moderate, fast), trend_scores(fast, moderate)
    gap_before = (m["synthetic-b"] - m["synthetic-a"]) * weights.trend
    gap_after = (f["synthetic-b"] - f["synthetic-a"]) * weights.trend
    assert gap_after > gap_before
    # B's skill credit trails A's by the midpoint of the two trend gaps.
    level_b = 3 * (1 - (gap_before + gap_after) / 2 / weights.skill)
    profile = MatchProfile(skills={"synthetic-a": 3, "synthetic-b": level_b})
    roles = [
        Role("synthetic-role-a", (RoleSkill("synthetic-a", 1, required_level=3),)),
        Role("synthetic-role-b", (RoleSkill("synthetic-b", 1, required_level=3),)),
    ]
    before = rank_roles(profile, roles, moderate, reference_velocities=fast)
    after = rank_roles(profile, roles, fast, reference_velocities=moderate)
    assert before[0].role_id == "synthetic-role-a"
    assert after[0].role_id == "synthetic-role-b"
