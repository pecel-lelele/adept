from copy import deepcopy

import pytest

from app.core.auth import CurrentUser
from app.features.pathway import service as pathway
from app.features.sdg import service


@pytest.mark.parametrize("count", [4, 5])
def test_regional_privacy_counts_distinct_people_not_organisation_rows(
    count: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = pathway.get_pathway(
        CurrentUser("aisyah", "Synthetic", "learner"), "data-analyst", "moderate"
    )
    plans = {f"synthetic-{n}": deepcopy(plan) for n in range(count)}
    monkeypatch.setattr(
        service.repository, "orgs_in_state", lambda state: ["synthetic-a", "synthetic-b"]
    )
    monkeypatch.setattr(service.org_service, "member_plans", lambda *args: deepcopy(plans))
    result = service.region_contribution("Synthetic State", "moderate", "data-analyst")
    assert result.minimum_people == 5
    assert result.aggregation_status == ("suppressed" if count < 5 else "available")
    assert result.role_ids == []
    if count < 5:
        assert result.links == result.goals_summary == result.target_contributions == []
    else:
        assert result.links and result.goals_summary
        assert all(goal.contributors == 5 for goal in result.goals_summary)
