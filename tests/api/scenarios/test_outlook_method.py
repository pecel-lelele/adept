"""Scenario parameters and role outlooks are computed from trend snapshots, not hard-coded."""

from fastapi.testclient import TestClient

from app.contracts.scenarios import OutlookResponse, ScenarioListResponse
from app.features.scenarios import service


def test_adoption_rate_is_mean_exposure_and_fast_is_amplified() -> None:
    assert service.adoption_rate([0.2, 0.4], "moderate") == 0.3
    assert service.adoption_rate([0.2, 0.4], "fast") == round((0.5 + 1.0) / 2, 3)
    assert service.adoption_rate([], "fast") == 0.0


def test_role_signal_weights_by_importance_and_reports_coverage() -> None:
    signal, coverage = service.role_signal(
        [("a", 3.0), ("b", 1.0), ("c", 1.0)], {"a": 0.2, "b": -0.2}
    )
    assert round(signal or 0, 4) == round((3 * 0.2 - 0.2) / 4, 4)
    assert coverage == 0.8
    assert service.role_signal([("x", 1.0)], {}) == (None, 0.0)


def test_outlook_stays_a_valid_demand_index() -> None:
    assert service.outlook_range([-1.4, 2.0], -1.4, 1.0) == (0.5, 2.0)
    assert service.clip(-3) == -0.5 and service.clip(3) == 1.0


def test_range_spans_history_and_widens_with_missing_coverage() -> None:
    assert service.outlook_range([0.1, 0.3], 0.3, 1.0) == (1.1, 1.3)
    low, high = service.outlook_range([0.1, 0.3], 0.3, 0.5)
    assert low < 1.1 and high > 1.3


def test_endpoints_cite_the_snapshot_sources(client: TestClient) -> None:
    scenarios = ScenarioListResponse.model_validate(client.get("/api/v1/scenarios").json())
    assert {s.id for s in scenarios.scenarios} == {"moderate", "fast"}
    fast = next(s for s in scenarios.scenarios if s.id == "fast")
    moderate = next(s for s in scenarios.scenarios if s.id == "moderate")
    assert fast.adoption_rate >= moderate.adoption_rate
    assert all(src.name != "MOCK DATA" for src in scenarios.meta.sources)

    outlook = OutlookResponse.model_validate(client.get("/api/v1/scenarios/outlook").json())
    assert outlook.outlooks and outlook.meta.is_estimate
    for o in outlook.outlooks:
        assert 0.5 <= o.low <= o.outlook <= o.high <= 2.0


def test_radar_signals_are_derived_from_the_snapshot(client: TestClient) -> None:
    body = client.get("/api/v1/trends/radar", params={"scenario": "fast"}).json()
    kinds = {i["entity_type"] for i in body["items"]}
    assert kinds == {"role", "skill"}
    assert all(src["name"] != "MOCK DATA" for src in body["meta"]["sources"])
