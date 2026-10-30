"""Score improvements use the production formula and real catalogue records."""

from dataclasses import replace

import pytest

from app.core.auth import CurrentUser
from app.features.matching import repository, sdg_weight, service
from app.features.matching.scoring import Weights, score_role, trend_scores
from app.features.matching.trend_port import fetch_snapshot
from app.features.pathway import data


@pytest.mark.parametrize("user_id", ["aisyah", "weijie", "ravi"])
def test_improvements_are_sorted_actual_score_deltas_with_cheapest_closing_courses(
    user_id: str,
) -> None:
    profile = repository.load_profile(user_id)
    roles = {role.role_id: role for role in repository.load_roles()}
    snapshot = fetch_snapshot("moderate")
    scores = trend_scores(snapshot.velocities)
    catalogue = data.catalogue()
    result = service.list_matches(CurrentUser(user_id, "Synthetic learner", "learner"), "moderate")
    assert any(match.improvements for match in result.matches)
    for match in result.matches:
        assert match.improvements == sorted(
            match.improvements, key=lambda i: (-i.score_gain, i.skill)
        )
        assert sum(c.weight * c.value for c in match.components) == pytest.approx(match.score)
        displayed = sum(round(c.weight * c.value * 100, 1) for c in match.components)
        assert displayed == pytest.approx(round(match.score * 100, 1), abs=0.15)
        role = roles[match.role_id]
        before = score_role(profile, role, scores, Weights()).score
        for item in match.improvements:
            req = next(r for r in role.skills if r.skill_id == item.skill)
            raised = replace(
                profile, skills={**profile.skills, item.skill: float(req.required_level)}
            )
            after = score_role(raised, role, scores, Weights()).score
            assert item.score_gain == pytest.approx(after - before)
            courses = [
                c
                for c in catalogue
                if item.skill in c.skill_ids
                and c.level >= req.required_level
                and c.format != "subscription"
            ]
            cheapest = min(courses, key=lambda c: (c.cost_myr, c.hours, c.id), default=None)
            assert item.course_id == (cheapest.id if cheapest else None)
            assert item.course_url == (cheapest.url if cheapest else None)


def test_no_closing_course_is_explicit_and_sdg_weight_scales_gains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(data, "catalogue", lambda: [])
    result = service.list_matches(CurrentUser("aisyah", "Synthetic learner", "learner"), "moderate")
    assert any(m.improvements for m in result.matches)
    for match in result.matches:
        assert all(i.course_id is None and i.course_url is None for i in match.improvements)
    weighted = sdg_weight.apply(result.matches, {}, 0.5)
    for match in weighted:
        original = next(m for m in result.matches if m.role_id == match.role_id)
        for improvement, before in zip(match.improvements, original.improvements, strict=True):
            assert improvement.score_gain == pytest.approx(before.score_gain / 2)
