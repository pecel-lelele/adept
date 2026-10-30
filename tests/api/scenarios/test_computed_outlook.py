"""Issue #80: each scenario reports its own weighted signal without a magnitude floor."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.features.scenarios import repository, service
from app.features.trends import mocks


@pytest.mark.parametrize(
    ("moderate", "fast"), [(0.14, 0.125), (-0.302, -0.112), (0.12, 0.0), (0.1, -0.05)]
)
def test_outlook_preserves_computed_fast_signal(
    monkeypatch: pytest.MonkeyPatch, moderate: float, fast: float
) -> None:
    snapshot = mocks.snapshot("moderate")
    item = snapshot.items[0].model_copy(
        update={"velocity_moderate": moderate, "velocity_fast": fast}
    )
    snapshot = snapshot.model_copy(update={"items": [item]})
    requirement = repository.role_requirements(repository.target_role_ids()[0])[0]
    requirement = replace(requirement, skill_id=item.skill_id)
    monkeypatch.setattr(repository, "history", lambda: [snapshot])
    monkeypatch.setattr(repository, "target_role_ids", lambda: ["synthetic-role"])
    monkeypatch.setattr(repository, "role_requirements", lambda _: [requirement])
    response = service.get_outlook("synthetic-role")
    by_scenario = {o.scenario: o for o in response.outlooks}
    assert by_scenario["fast"].outlook == round(1 + service.clip(fast), 3)
    assert by_scenario["moderate"].outlook == round(1 + service.clip(moderate), 3)
    for outlook in response.outlooks:
        assert outlook.low <= outlook.outlook <= outlook.high


@pytest.mark.parametrize("snapshot_date", mocks.AVAILABLE_MOCK_DATES)
def test_all_fixture_outlooks_equal_their_own_weighted_signals(
    monkeypatch: pytest.MonkeyPatch, snapshot_date: date
) -> None:
    snapshot = mocks.snapshot("moderate", snapshot_date)
    monkeypatch.setattr(repository, "history", lambda: [snapshot])
    response = service.get_outlook(None, snapshot_date)
    for outlook in response.outlooks:
        velocities = {
            i.skill_id: getattr(i, f"velocity_{outlook.scenario}") for i in snapshot.items
        }
        requirements = [
            (r.skill_id, r.importance) for r in repository.role_requirements(outlook.role_id)
        ]
        signal, _ = service.role_signal(requirements, velocities)
        assert signal is not None
        assert outlook.outlook == round(1 + service.clip(signal), 3), outlook.role_id
        assert outlook.low <= outlook.outlook <= outlook.high
    assert response.meta.snapshot_date == snapshot_date
    assert [s.model_dump() for s in response.meta.sources] == [
        s.model_dump() for s in snapshot.meta.sources
    ]
    assert response.meta.is_fallback == snapshot.meta.is_fallback


@pytest.mark.parametrize("path", ["/api/v1/scenarios", "/api/v1/scenarios/outlook"])
def test_comparison_metadata_describes_both_scenarios(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["meta"]["scenario"] == "both"


@pytest.mark.parametrize("path", ["/api/v1/matches", "/api/v1/trends/radar"])
def test_both_is_attribution_only_not_a_selectable_scenario(client: TestClient, path: str) -> None:
    assert client.get(path, params={"scenario": "both"}).status_code == 422
