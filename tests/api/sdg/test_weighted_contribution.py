"""Learning effort is weighted by hours, never presented as measured UN impact."""

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import mock_meta
from app.contracts.pathway import Pathway, PathwayStep
from app.contracts.sdg import SdgLink
from app.features.sdg import repository, service


@pytest.mark.parametrize(
    ("origins", "fallbacks", "expected"),
    [
        (["db"], [True], "db"),
        (["db", "db"], [False, True], "db"),
        (["fixture", "db"], [True, False], "fixture"),
        (["db", "fixture"], [False, True], "fixture"),
        (["db", None], [False, False], None),
    ],
)
def test_contribution_preserves_plan_origin_separately_from_fallback(
    origins: list[str | None], fallbacks: list[bool], expected: str | None
) -> None:
    plans = {}
    for index, (origin, fallback) in enumerate(zip(origins, fallbacks, strict=True)):
        plan = _plan((0, 0))
        plan.meta = plan.meta.model_copy(update={"served_from": origin, "is_fallback": fallback})
        plans[str(index)] = plan
    result = service.contribution_for_plans(plans, "organisation", "synthetic-org", "moderate")
    assert result.meta.served_from == expected
    assert result.meta.is_fallback == any(fallbacks)


def _plan(hours: tuple[float, float]) -> Pathway:
    return Pathway(
        role_id="data-analyst",
        total_weeks=2,
        total_hours=sum(hours),
        steps=[
            PathwayStep(
                order=index + 1,
                skill_id=f"synthetic-{index}",
                courses=[],
                est_hours=value,
                week_start=1,
                week_end=2,
                reason="Synthetic test step",
            )
            for index, value in enumerate(hours)
        ],
        meta=mock_meta().model_copy(update={"is_fallback": True, "served_from": "fixture"}),
    )


def test_hours_weight_targets_and_aggregate_people_without_double_counting_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = repository.targets()

    def links(skill: str) -> list[SdgLink]:
        ids = ["4.4", "4.4", "8.2"] if skill == "synthetic-0" else ["8.2"]
        return [
            SdgLink(target=targets[target], reason="Synthetic mapping for hour-weighting test")
            for target in ids
        ]

    monkeypatch.setattr(repository, "skill_links", links)
    result = service.contribution_for_plans(
        {"synthetic-person": _plan((8, 2))}, "person", "synthetic-person", "moderate"
    )
    shares = {item.target.target: item for item in result.target_contributions}
    assert shares["4.4"].planned_hours == 8
    assert shares["4.4"].hours_share == pytest.approx(0.8)
    assert shares["8.2"].hours_share == 1
    assert result.meta.is_fallback and result.meta.served_from == "fixture"
    aggregate = service.contribution_for_plans(
        {"a": _plan((8, 2)), "b": _plan((0, 20))}, "organisation", "synthetic-org", "moderate"
    )
    target4 = next(item for item in aggregate.target_contributions if item.target.target == "4.4")
    assert target4.hours_share == pytest.approx(8 / 30)
    goal4 = next(item for item in aggregate.goals_summary if item.goal == 4)
    assert goal4.hours_share == pytest.approx(8 / 30)
    zero = service.contribution_for_plans({"a": _plan((0, 0))}, "person", "a", "moderate")
    assert zero.target_contributions == []
    assert all(goal.hours_share == 0 for goal in zero.goals_summary)


def test_every_match_sdg_badge_contains_a_catalogue_reason_and_strength(client: TestClient) -> None:
    response = client.get("/api/v1/matches", headers={"X-Demo-User": "aisyah"})
    assert response.status_code == 200
    for match in response.json()["matches"]:
        links = {link.target.target: link for link in repository.role_links(match["role_id"])}
        for target in match["sdg_targets"]:
            assert target["reason"] == links[target["target"]].reason
            assert target["reason"].strip()
            assert target["strength"] == links[target["target"]].strength
