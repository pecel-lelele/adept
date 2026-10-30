import pytest
from harness.fixtures import PROFILES

from app.core.auth import CurrentUser
from app.features.matching import service
from app.features.matching.scoring import MatchProfile, Role, RoleSkill, rank_roles, trend_scores


@pytest.mark.parametrize("user_id", list(PROFILES))
def test_every_demo_profile_has_a_role_score_change_over_half_a_point(user_id: str) -> None:
    user = CurrentUser(user_id, "Synthetic learner", "learner")
    moderate = service.list_matches(user, "moderate").matches
    fast = service.list_matches(user, "fast").matches
    before = {match.role_id: match.score for match in moderate}
    after = {match.role_id: match.score for match in fast}
    assert any(abs(before[role] - after[role]) > 0.005 for role in before), user_id


def test_trend_scale_is_shared_between_both_scenarios() -> None:
    before = {"same": 0.05, "moving": 0.01}
    after = {"same": 0.05, "moving": 0.1}
    moderate = trend_scores(before, after)
    fast = trend_scores(after, before)
    assert moderate["same"] == fast["same"]
    assert moderate["moving"] < fast["moving"]
    assert trend_scores({"declining": -0.1, "neutral": 0, "rising": 0.1}) == {
        "declining": 0.0,
        "neutral": 0.5,
        "rising": 1.0,
    }


def test_near_tie_flips_with_fast_velocity_before_shared_normalization() -> None:
    profile = MatchProfile(skills={"synthetic-a": 3, "synthetic-b": 2})
    roles = [
        Role("synthetic-role-a", (RoleSkill("synthetic-a", 1, required_level=3),)),
        Role("synthetic-role-b", (RoleSkill("synthetic-b", 1, required_level=3),)),
    ]
    moderate = {"synthetic-a": 0.1, "synthetic-b": 0.2}
    fast = {skill: value * 1.5 for skill, value in moderate.items()}
    before = rank_roles(profile, roles, moderate, reference_velocities=fast)
    after = rank_roles(profile, roles, fast, reference_velocities=moderate)
    assert before[0].role_id == "synthetic-role-a"
    assert after[0].role_id == "synthetic-role-b"
