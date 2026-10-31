"""Issue #78: declaring a relevant interest cannot penalise a match."""

from dataclasses import replace

import pytest

from app.features.matching import repository
from app.features.matching.scoring import (
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    interest_fit,
    score_role,
)


@pytest.mark.parametrize("interests", [{"data"}, {"DATA"}, {"data", "other", "extra"}])
def test_matching_interest_never_lowers_score(interests: set[str]) -> None:
    role = Role("synthetic-role", (RoleSkill("python", 1.0),), frozenset({"data", "ai", "tech"}))
    neutral_profile = MatchProfile({"python": 1.0})
    profile = replace(neutral_profile, interests=frozenset(interests))
    baseline = score_role(neutral_profile, role, {"python": NEUTRAL}, Weights())
    result = score_role(profile, role, {"python": NEUTRAL}, Weights())
    assert result.score > baseline.score
    assert result.breakdown["interest"] == pytest.approx(NEUTRAL + (1 - NEUTRAL) / len(interests))


def test_interest_casefold_deduplicates_before_comparing() -> None:
    profile = MatchProfile({}, frozenset({"STRASSE", "Straße"}))
    role = Role("synthetic-role", (), frozenset({"straße", "extra"}))
    assert interest_fit(profile, role) == 1.0


def test_untagged_role_is_neutral_with_declared_interests() -> None:
    role = Role("synthetic-role", ())
    profile = MatchProfile({}, frozenset({"data"}))
    result = score_role(profile, role, {}, Weights())
    assert interest_fit(profile, role) == NEUTRAL
    assert (
        result.score
        == score_role(replace(profile, interests=frozenset()), role, {}, Weights()).score
    )
    component = repository.score_components(result, "moderate")[-1]
    assert component.value == NEUTRAL
    assert component.provided is True
    assert "neutral" in component.explanation.lower()


def test_no_interests_preserves_neutral_score_and_not_provided() -> None:
    role = Role("synthetic-role", (RoleSkill("python", 1.0),), frozenset({"data"}))
    result = score_role(MatchProfile({"python": 1.0}), role, {"python": NEUTRAL}, Weights())
    weights = Weights()
    assert interest_fit(MatchProfile({}), role) is None
    assert result.score == pytest.approx(
        weights.skill + (weights.trend + weights.interest) * NEUTRAL
    )
    component = repository.score_components(result, "moderate")[-1]
    assert component.value == NEUTRAL
    assert component.provided is False


def test_unmatched_interests_are_neutral() -> None:
    assert (
        interest_fit(
            MatchProfile({}, frozenset({"other"})), Role("synthetic-role", (), frozenset({"data"}))
        )
        == NEUTRAL
    )
