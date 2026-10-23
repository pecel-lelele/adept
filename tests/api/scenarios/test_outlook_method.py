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


# ===========================================================================
# Bug 1 — score_rows() must cover the full skill catalogue (not just exposure_map keys)
# ===========================================================================

import pytest

from pipelines.trends.score import DEFAULT_EXPOSURE, score_rows


class TestScoreRowsFullCatalogue:
    """score_rows() must include every skill ID in the provided skill_ids set,
    even those absent from the exposure_map (canonical_skills.csv)."""

    def _inputs(self):
        counts = {"skill_a": 10.0, "skill_b": 5.0, "skill_c": 3.0}
        labor = {"skill_a": (0.1, "bls"), "skill_b": (-0.2, "bls")}
        exposure = {"skill_a": 0.7, "skill_b": 0.3}  # skill_c intentionally absent
        return counts, labor, exposure

    def test_without_skill_ids_drops_uncovered_skill(self) -> None:
        counts, labor, exposure = self._inputs()
        rows = score_rows(counts, 100, counts, 100, labor, exposure, skill_ids=None)
        assert "skill_c" not in {r["skill_id"] for r in rows}

    def test_with_skill_ids_includes_uncovered_skill(self) -> None:
        counts, labor, exposure = self._inputs()
        full = {"skill_a", "skill_b", "skill_c"}
        rows = score_rows(counts, 100, counts, 100, labor, exposure, skill_ids=full)
        assert {r["skill_id"] for r in rows} == full

    def test_uncovered_skill_gets_default_exposure(self) -> None:
        counts, labor, exposure = self._inputs()
        rows = score_rows(counts, 100, counts, 100, labor, exposure, skill_ids={"skill_a", "skill_b", "skill_c"})
        row_c = next(r for r in rows if r["skill_id"] == "skill_c")
        assert row_c["automation_exposure"] == pytest.approx(DEFAULT_EXPOSURE, abs=1e-6)

    def test_canonical_skills_scores_unchanged(self) -> None:
        counts, labor, exposure = self._inputs()
        without = {r["skill_id"]: r for r in score_rows(counts, 100, counts, 100, labor, exposure)}
        with_ = {r["skill_id"]: r for r in score_rows(counts, 100, counts, 100, labor, exposure, skill_ids={"skill_a", "skill_b", "skill_c"})}
        for sid in ("skill_a", "skill_b"):
            for key in ("velocity_moderate", "velocity_fast", "automation_exposure"):
                assert with_[sid][key] == pytest.approx(without[sid][key], abs=1e-9)

    def test_output_count_equals_full_catalogue_count(self) -> None:
        counts, labor, exposure = self._inputs()
        full = {"skill_a", "skill_b", "skill_c", "skill_d", "skill_e"}
        rows = score_rows(counts, 100, counts, 100, labor, exposure, skill_ids=full)
        assert len(rows) == len(full)


# ===========================================================================
# Bug 2 — enforce_fast_magnitude: |fast| must be >= |moderate| at role level
# ===========================================================================

from app.features.scenarios.service import enforce_fast_magnitude


class TestEnforceFastMagnitude:
    def test_adversarial_mix_bug_reproduces_then_fixed(self) -> None:
        """Adversarial: role_moderate=0.14, role_fast=0.125 (before fix). Bug confirmed."""
        role_moderate = 0.14
        role_fast_buggy = 0.125
        assert abs(role_fast_buggy) < abs(role_moderate), "Precondition: bug must exist"
        fixed = enforce_fast_magnitude(role_moderate, role_fast_buggy)
        assert abs(fixed) >= abs(role_moderate)
        assert fixed >= 0, "Direction must be preserved"

    def test_already_satisfied_unchanged(self) -> None:
        assert enforce_fast_magnitude(0.10, 0.20) == pytest.approx(0.20)

    def test_negative_direction_preserved(self) -> None:
        fixed = enforce_fast_magnitude(-0.15, -0.08)
        assert abs(fixed) >= 0.15
        assert fixed <= 0

    def test_opposite_sign_not_adjusted(self) -> None:
        assert enforce_fast_magnitude(0.10, -0.05) == pytest.approx(-0.05)

    def test_zero_fast_same_direction_gets_floor(self) -> None:
        assert abs(enforce_fast_magnitude(0.12, 0.0)) >= 0.12


# ===========================================================================
# Bug 3 — outlook_range: nonzero width at near-zero signal + low coverage
# ===========================================================================

from app.features.scenarios.service import MIN_COVERAGE_THRESHOLD, BASE_UNCERTAINTY, outlook_range as _range


class TestOutlookRangeBug3:
    def test_near_zero_signal_low_coverage_nonzero_range(self) -> None:
        low, high = _range([0.001], 0.001, 0.02)
        assert low != high, f"Near-zero signal + low coverage must produce range. Got {low}, {high}"
        assert high > low

    def test_near_zero_signal_high_coverage_narrow_range(self) -> None:
        low, high = _range([0.001], 0.001, 0.95)
        assert high > low
        assert (high - low) < 0.10, f"High-coverage should be narrow. Got width={(high-low):.4f}"

    def test_large_signal_low_coverage_wide_range(self) -> None:
        low, high = _range([0.40], 0.40, 0.10)
        assert (high - low) > 0.10

    def test_full_coverage_zero_widen(self) -> None:
        low, high = _range([0.20], 0.20, 1.0)
        assert low == pytest.approx(high, abs=0.001)

    def test_constants_are_set(self) -> None:
        assert MIN_COVERAGE_THRESHOLD == pytest.approx(0.20)
        assert BASE_UNCERTAINTY > 0

