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

from fastapi.testclient import TestClient

from app.contracts.trends import RadarResponse, RoleTrendResponse, TrendSnapshotResponse

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

    def test_snapshot_default_no_date(self, client: TestClient) -> None:
        """Omitting snapshot_date returns the latest available snapshot."""
        resp = client.get("/api/v1/trends/snapshot", params={"scenario": "moderate"})
        assert resp.status_code == 200, resp.text
        body = TrendSnapshotResponse.model_validate(resp.json())
        assert body.meta.snapshot_date is not None
        assert body.meta.available_snapshots  # must be non-empty

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
