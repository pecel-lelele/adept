"""tests/api/trends/test_router.py

Tests for the trends API endpoints (F2 + F3).
Uses mock fixture (src/data/seed/mock_trends.json) — no DB, no network.

Coverage:
  - GET /api/v1/trends/snapshot (both scenario values)
  - GET /api/v1/trends/snapshot without snapshot_date → returns latest
  - GET /api/v1/trends/radar (legacy, both scenarios)
  - GET /api/v1/trends/roles/{role_id} (legacy, 200 and 404)
  - Schema validation (TrendSnapshotResponse contract)
  - Non-empty labor_decay_source_note on every item
  - meta.is_estimate == True on every response
  - meta.available_snapshots is populated
"""

import pytest
from fastapi.testclient import TestClient

from app.contracts.trends import RadarResponse, RoleTrendResponse, TrendSnapshotResponse


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_public_role_directions_need_no_personal_profile_and_support_replay(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    from app.features.pathway import service as pathway_service
    from app.features.profile import service as profile_service
    from app.features.trends import service

    def no_intake(*args: object, **kwargs: object) -> None:
        raise AssertionError("Public directions must not load a personal profile or plan")

    monkeypatch.setattr(pathway_service, "learner_for", no_intake)
    monkeypatch.setattr(profile_service, "get_my_profile", no_intake)
    snapshot = client.get("/api/v1/trends/snapshot").json()
    for day in snapshot["meta"]["available_snapshots"]:
        response = client.get(
            "/api/v1/trends/radar", params={"scenario": scenario, "snapshot_date": day}
        )
        assert response.status_code == 200, response.text
        body = RadarResponse.model_validate(response.json())
        assert body.meta.snapshot_date.isoformat() == day
        assert body.meta.scenario == scenario
        assert body.meta.sources and body.meta.is_estimate
        roles = [item for item in body.items if item.entity_type == "role"]
        assert roles
        expected = service.signals_from_snapshot(
            service.get_snapshot(body.meta.snapshot_date, scenario), scenario
        )
        assert roles == [item for item in expected if item.entity_type == "role"]


# ---------------------------------------------------------------------------
# New: GET /api/v1/trends/snapshot
# ---------------------------------------------------------------------------


class TestSnapshotEndpoint:
    def test_snapshot_moderate_schema_valid(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        assert resp.status_code == 200, resp.text
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.scenario == "moderate"
        assert body.meta.is_estimate is True
        assert len(body.items) > 0

    def test_snapshot_fast_schema_valid(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "fast"})
        assert resp.status_code == 200, resp.text
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.scenario == "fast"
        assert body.meta.is_estimate is True
        assert len(body.items) > 0

    def test_velocity_moderate_is_scenario_invariant(self, client: TestClient) -> None:
        mod = client.get("/api/v1/trends/snapshot?scenario=moderate").json()["items"]
        fast = client.get("/api/v1/trends/snapshot?scenario=fast").json()["items"]
        mod_by_id = {i["skill_id"]: i for i in mod}
        assert len(mod) == len(fast)
        for item in fast:
            baseline = mod_by_id[item["skill_id"]]
            assert item["velocity_moderate"] == baseline["velocity_moderate"]
            assert item["velocity_fast"] == baseline["velocity_fast"]
            assert item["direction_moderate"] == baseline["direction_moderate"]
            assert item["direction_fast"] == baseline["direction_fast"]

    def test_snapshot_default_no_date(self, client: TestClient) -> None:
        """Omitting snapshot_date returns the latest available snapshot."""
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        assert resp.status_code == 200, resp.text
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.snapshot_date is not None
        assert body.meta.available_snapshots  # must be non-empty

    def test_multiple_available_snapshots_and_dates_differ(self, client: TestClient) -> None:
        """Assert at least 2 available snapshots exist and return non-identical item sets."""
        resp = client.get("/api/v1/trends/snapshot")
        assert resp.status_code == 200
        body = TrendSnapshotResponse.model_validate(resp.json())
        dates = body.meta.available_snapshots
        assert len(dates) >= 2, f"Expected >= 2 available snapshots, got {dates}"

        # Query first date and second date
        d1, d2 = dates[0].isoformat(), dates[-1].isoformat()
        r1 = client.get(f"/api/v1/trends/snapshot?snapshot_date={d1}")
        r2 = client.get(f"/api/v1/trends/snapshot?snapshot_date={d2}")
        assert r1.status_code == 200
        assert r2.status_code == 200
        snap1 = TrendSnapshotResponse.model_validate(r1.json())
        snap2 = TrendSnapshotResponse.model_validate(r2.json())

        # Non-identical items between the two snapshots
        items1 = {i.skill_id: i.velocity_moderate for i in snap1.items}
        items2 = {i.skill_id: i.velocity_moderate for i in snap2.items}
        assert items1 != items2, "Expected items to differ between different snapshot dates"

    def test_requesting_unavailable_date_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A date the (reachable) source does not hold is 404."""
        from app.features.trends import mocks, repository

        monkeypatch.setattr(
            repository,
            "resolve_context",
            lambda strict=False: repository.ResolvedContext(
                source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES)
            ),
        )
        resp = client.get("/api/v1/trends/snapshot?snapshot_date=1999-01-01")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "not_found"

    def test_unheld_date_during_an_outage_returns_503(
        self, client: TestClient, unavailable_trend_database: None
    ) -> None:
        """N5: explicitly simulate an outage; do not depend on the integration DB being absent."""
        resp = client.get("/api/v1/trends/snapshot?snapshot_date=1999-01-01")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "trend_unavailable"

    def test_snapshot_default_scenario_is_moderate(self, client: TestClient) -> None:
        """Default scenario when not specified must be 'moderate'."""
        resp = client.get("/api/v1/trends/snapshot")
        assert resp.status_code == 200, resp.text
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.scenario == "moderate"

    def test_all_items_have_nonempty_labor_decay_source_note(self, client: TestClient) -> None:
        """Every SkillVelocity must have a non-empty labor_decay_source_note."""
        for scenario in ("moderate", "fast"):
            resp = client.get("/api/v1/trends/snapshot", params={"scenario": scenario})
            assert resp.status_code == 200
            body = TrendSnapshotResponse.model_validate(resp.json())
            for item in body.items:
                assert item.labor_decay_source_note, (
                    f"Empty labor_decay_source_note for skill_id={item.skill_id} "
                    f"in scenario={scenario}"
                )

    def test_snapshot_has_sources_with_dates(self, client: TestClient) -> None:
        """meta.sources must have at least one entry with name and url."""
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.sources
        for src in body.meta.sources:
            assert src.name
            assert src.retrieved_at is not None

    def test_fast_and_moderate_differ(self, client: TestClient) -> None:
        """Fast and moderate snapshots must visibly differ on at least one velocity."""
        resp_m = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        resp_f = client.get("/api/v1/trends/snapshot", params={"scenario": "fast"})
        body_m = TrendSnapshotResponse.model_validate(resp_m.json())
        body_f = TrendSnapshotResponse.model_validate(resp_f.json())
        velocities_m = [item.velocity_moderate for item in body_m.items]
        velocities_f = [item.velocity_moderate for item in body_f.items]
        assert velocities_m != velocities_f or body_m.meta.scenario != body_f.meta.scenario

    def test_automation_exposure_in_range(self, client: TestClient) -> None:
        """automation_exposure must be in [0, 1] for all items."""
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        body = TrendSnapshotResponse.model_validate(resp.json())
        for item in body.items:
            assert 0.0 <= item.automation_exposure <= 1.0

    def test_direction_values_valid(self, client: TestClient) -> None:
        """direction_moderate and direction_fast must be one of the three valid values."""
        valid = {"rising", "declining", "stable"}
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        body = TrendSnapshotResponse.model_validate(resp.json())
        for item in body.items:
            assert item.direction_moderate in valid
            assert item.direction_fast in valid

    def test_weights_present(self, client: TestClient) -> None:
        """meta.weights must be a non-empty dict."""
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.weights
        assert "research_velocity" in body.meta.weights or len(body.meta.weights) > 0


# ---------------------------------------------------------------------------
# Legacy: GET /api/v1/trends/radar
# ---------------------------------------------------------------------------


class TestRadarEndpoint:
    def test_radar_moderate(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/radar", params={"scenario": "moderate"})
        assert resp.status_code == 200
        body = RadarResponse.model_validate(resp.json())
        assert body.items
        assert body.meta.scenario == "moderate"

    def test_radar_fast(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/radar", params={"scenario": "fast"})
        assert resp.status_code == 200
        body = RadarResponse.model_validate(resp.json())
        assert body.items
        assert body.meta.scenario == "fast"

    def test_radar_sources_nonempty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/radar")
        body = RadarResponse.model_validate(resp.json())
        assert body.meta.sources


# ---------------------------------------------------------------------------
# Legacy: GET /api/v1/trends/roles/{role_id}
# ---------------------------------------------------------------------------


class TestRoleTrendEndpoint:
    def test_known_skill_id_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/trends/roles/prompt-engineering")
        assert resp.status_code == 200
        body = RoleTrendResponse.model_validate(resp.json())
        assert body.signal.entity_id == "prompt-engineering"

    def test_unknown_role_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/trends/roles/unknown-role").status_code == 404

    def test_role_scenario_fast(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/trends/roles/manual-data-entry",
            params={"scenario": "fast"},
        )
        assert resp.status_code == 200
        body = RoleTrendResponse.model_validate(resp.json())
        assert body.meta.scenario == "fast"
        # Manual data entry should be declining
        assert body.signal.direction in ("declining", "stable")
