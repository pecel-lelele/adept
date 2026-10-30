"""Ranks are verified by independent requests through the production matching boundary."""

from dataclasses import replace

import pytest

from app.core.auth import CurrentUser
from app.features.matching import repository, service

USER = CurrentUser("aisyah", "Synthetic learner", "learner")


@pytest.mark.parametrize("weight", [0.0, 0.3729, 1.0])
def test_other_scenario_is_same_profile_snapshot_and_weight(weight: float) -> None:
    selected = service.list_matches(USER, "fast", sdg_weight_value=weight)
    other = service.list_matches(USER, "moderate", selected.meta.snapshot_date, weight)
    by_id = {m.role_id: m for m in other.matches}
    for pos, match in enumerate(selected.matches, 1):
        assert match.rank == pos
        alternative = by_id[match.role_id]
        assert match.other_scenario == "moderate"
        assert match.other_rank == alternative.rank
        assert match.other_score == alternative.score
        assert alternative.other_rank == match.rank
        assert alternative.other_score == match.score


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("weight", [0.0, 0.3729, 1.0])
def test_new_rank_reranks_all_roles_after_the_skill_change(
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    weight: float,
) -> None:
    profile = repository.load_profile(USER.id)
    result = service.list_matches(USER, scenario, sdg_weight_value=weight)
    roles = {r.role_id: r for r in repository.load_roles()}
    for match in (result.matches[0], result.matches[-1]):
        for item in match.improvements[:3]:
            req = next(r for r in roles[match.role_id].skills if r.skill_id == item.skill)
            raised = replace(
                profile, skills={**profile.skills, item.skill: float(req.required_level)}
            )
            with monkeypatch.context() as patch:
                patch.setattr(repository, "_load_profile", lambda _user, value=raised: value)
                actual = service.list_matches(USER, scenario, result.meta.snapshot_date, weight)
            expected = next(
                i for i, m in enumerate(actual.matches, 1) if m.role_id == match.role_id
            )
            assert item.new_rank == expected
    detail = service.get_match(
        USER, result.matches[0].role_id, scenario, result.meta.snapshot_date, weight
    )
    assert detail == result.matches[0]
