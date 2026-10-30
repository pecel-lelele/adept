"""Dummy-only tests of the prepared matching harness; no scoring evidence is generated."""

from datetime import date
from importlib import import_module

import pytest

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.matching import MatchResponse, RoleMatch
from app.contracts.profile import Profile, UserSkill
from app.core.auth import CurrentUser
from app.features.profile import service as profile_service


def _profile() -> Profile:
    return Profile(
        user_id="synthetic-counterfactual",
        display_name="Synthetic fixture",
        segment="working",
        hours_per_week=4,
        budget_myr=0,
        hrd_eligible=False,
        skills=[UserSkill(skill_id="python", level=2, source="confirmed")],
    )


def _response(score: float = 0.5) -> MatchResponse:
    meta = mock_meta()
    return MatchResponse(
        matches=[
            RoleMatch(
                role_id=role,
                label="Synthetic fixture",
                score=value,
                components=[],
                missing_skills=[],
                partial_skills=[],
                sdg_targets=[],
                meta=meta,
            )
            for role, value in [("synthetic-role-a", score), ("synthetic-role-b", 0.4)]
        ],
        meta=meta,
    )


def test_identical_inputs_and_restore_after_comparison() -> None:
    harness = import_module("pipelines.guardrails.matching_counterfactual")
    original = profile_service.get_my_profile
    observed: list[tuple[int, str, str]] = []

    def dummy(user: CurrentUser, scenario: ScenarioId, snapshot_date: date) -> MatchResponse:
        profile = profile_service.get_my_profile(user.id)
        assert profile.skills == _profile().skills
        observed.append((profile.age, profile.gender, profile.background))
        return _response()

    harness.check_matching_counterfactual(_profile(), date(2026, 10, 20), query=dummy)
    assert len(observed) == len(set(observed)) == 5
    assert profile_service.get_my_profile is original


@pytest.mark.parametrize("difference", ["score", "ranking", "empty"])
def test_detects_differences_and_rejects_empty_outputs(difference: str) -> None:
    harness = import_module("pipelines.guardrails.matching_counterfactual")
    original = profile_service.get_my_profile

    def dummy(user: CurrentUser, scenario: ScenarioId, snapshot_date: date) -> MatchResponse:
        profile = profile_service.get_my_profile(user.id)
        response = _response(0.6 if difference == "score" and profile.age == 41 else 0.5)
        if difference == "ranking" and profile.age == 41:
            response.matches.reverse()
        if difference == "empty":
            response.matches = []
        return response

    with pytest.raises(AssertionError):
        harness.check_matching_counterfactual(_profile(), date(2026, 10, 20), query=dummy)
    assert profile_service.get_my_profile is original
