"""Scenario parameters and role outlooks are computed from trend snapshots, not hard-coded."""

import pytest
from fastapi.testclient import TestClient

from app.contracts.scenarios import OutlookResponse, ScenarioListResponse
from app.features.scenarios import service
from app.features.scenarios.service import (
    BASE_UNCERTAINTY,
    MIN_COVERAGE_THRESHOLD,
)
from app.features.scenarios.service import (
    outlook_range as _range,
)
from pipelines.trends.score import DEFAULT_EXPOSURE, score_rows


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
        rows = score_rows(
            counts,
            100,
            counts,
            100,
            labor,
            exposure,
            skill_ids={"skill_a", "skill_b", "skill_c"},
        )
        row_c = next(r for r in rows if r["skill_id"] == "skill_c")
        assert row_c["automation_exposure"] == pytest.approx(DEFAULT_EXPOSURE, abs=1e-6)

    def test_canonical_skills_scores_unchanged(self) -> None:
        counts, labor, exposure = self._inputs()
        without = {r["skill_id"]: r for r in score_rows(counts, 100, counts, 100, labor, exposure)}
        with_ = {
            r["skill_id"]: r
            for r in score_rows(
                counts,
                100,
                counts,
                100,
                labor,
                exposure,
                skill_ids={"skill_a", "skill_b", "skill_c"},
            )
        }
        for sid in ("skill_a", "skill_b"):
            for key in ("velocity_moderate", "velocity_fast", "automation_exposure"):
                assert with_[sid][key] == pytest.approx(without[sid][key], abs=1e-9)

    def test_output_count_equals_full_catalogue_count(self) -> None:
        counts, labor, exposure = self._inputs()
        full = {"skill_a", "skill_b", "skill_c", "skill_d", "skill_e"}
        rows = score_rows(counts, 100, counts, 100, labor, exposure, skill_ids=full)
        assert len(rows) == len(full)

    def test_has_evidence_true_for_measured_skills(self) -> None:
        """skill_a and skill_b have signal counts and/or BLS data → has_evidence=True."""
        counts, labor, exposure = self._inputs()
        rows = score_rows(counts, 100, counts, 100, labor, exposure)
        by_id = {r["skill_id"]: r for r in rows}
        assert by_id["skill_a"]["has_evidence"] is True  # arxiv counts + BLS
        assert by_id["skill_b"]["has_evidence"] is True  # arxiv counts + BLS

    def test_has_evidence_false_for_catalogue_only_skill(self) -> None:
        """skill_c: in catalogue, no arxiv counts, no BLS mapping → has_evidence=False.

        We explicitly exclude skill_c from the signal counts to simulate a skill that
        exists in the DB catalogue but was never measured by any arxiv period or BLS entry.
        """
        _, labor, exposure = self._inputs()
        counts_no_c = {"skill_a": 10.0, "skill_b": 5.0}  # skill_c intentionally absent
        rows = score_rows(
            counts_no_c,
            100,
            counts_no_c,
            100,
            labor,
            exposure,
            skill_ids={"skill_a", "skill_b", "skill_c"},
        )
        row_c = next(r for r in rows if r["skill_id"] == "skill_c")
        assert row_c["has_evidence"] is False

    def test_has_evidence_true_when_only_bls_no_arxiv(self) -> None:
        """skill_d: no arxiv counts but has a BLS mapping → still has_evidence=True."""
        empty_counts: dict[str, float] = {}
        labor_with_d = {"skill_d": (0.05, "bls")}
        rows = score_rows(
            empty_counts,
            100,
            empty_counts,
            100,
            labor_with_d,
            {},
            skill_ids={"skill_d"},
        )
        assert rows[0]["has_evidence"] is True


# ===========================================================================
# Issue 3 — write_snapshots / publish must exclude has_evidence=False rows
# ===========================================================================


class TestHasEvidenceFiltering:
    """Rows with has_evidence=False must never reach trend_snapshots so that
    role_signal() cannot count catalogue-only skills as covered."""

    def test_default_only_skill_flagged_not_evidenced(self) -> None:
        """A skill with zero arxiv counts and no BLS entry gets has_evidence=False."""
        counts: dict[str, float] = {}
        rows = score_rows(
            counts,
            1,
            counts,
            1,
            {},
            {},
            skill_ids={"ghost_skill"},
        )
        assert len(rows) == 1
        assert rows[0]["has_evidence"] is False

    def test_arxiv_signal_in_t1_only_is_sufficient_evidence(self) -> None:
        """A brand-new skill that only appears in t1 (not t0) still has evidence."""
        rows = score_rows(
            {},
            100,
            {"new_skill": 5.0},
            100,
            {},
            {},
            skill_ids={"new_skill"},
        )
        assert rows[0]["has_evidence"] is True

    def test_evidenced_and_non_evidenced_split_correctly(self) -> None:
        """score_rows returns both kinds; callers are responsible for filtering."""
        counts = {"measured": 10.0}
        rows = score_rows(
            counts,
            100,
            counts,
            100,
            {},
            {},
            skill_ids={"measured", "ghost"},
        )
        by_id = {r["skill_id"]: r for r in rows}
        assert by_id["measured"]["has_evidence"] is True
        assert by_id["ghost"]["has_evidence"] is False

    def test_stale_rows_excluded_by_evidenced_filter(self) -> None:
        """Simulates a rescore: first run emits a skill; second run drops its evidence.

        write_snapshots / publish must delete all rows for the date first so the
        stale row from run-1 cannot inflate coverage in run-2.  This test verifies
        the filtering contract: the set of rows passed to the DB write contains only
        evidenced rows, and the ghost skill (has_evidence=False) is absent.
        """
        counts_run1 = {"skill_x": 5.0, "skill_y": 3.0}  # both evidenced
        rows_run1 = score_rows(
            counts_run1,
            100,
            counts_run1,
            100,
            {},
            {},
            skill_ids={"skill_x", "skill_y"},
        )
        assert all(r["has_evidence"] for r in rows_run1), "run-1: both should be evidenced"

        # Run 2: skill_y loses its arxiv signal → should become has_evidence=False
        counts_run2: dict[str, float] = {"skill_x": 7.0}  # skill_y absent
        rows_run2 = score_rows(
            counts_run2,
            100,
            counts_run2,
            100,
            {},
            {},
            skill_ids={"skill_x", "skill_y"},
        )
        evidenced_run2 = [r for r in rows_run2 if r.get("has_evidence", True)]
        evidenced_ids = {r["skill_id"] for r in evidenced_run2}

        # skill_y must NOT appear in the evidenced set that goes to the DB
        assert "skill_y" not in evidenced_ids, (
            "skill_y lost its evidence in run-2; it must be excluded from the DB write"
        )
        assert "skill_x" in evidenced_ids


# ===========================================================================
# Issue #80 — computed-signal regressions live in test_computed_outlook.py
# ===========================================================================


# ===========================================================================
# Bug 3 — outlook_range: nonzero width at near-zero signal + low coverage
# ===========================================================================


class TestOutlookRangeBug3:
    def test_near_zero_signal_low_coverage_nonzero_range(self) -> None:
        low, high = _range([0.001], 0.001, 0.02)
        assert low != high, f"Near-zero + low coverage must produce range. Got {low}, {high}"
        assert high > low

    def test_near_zero_signal_high_coverage_narrow_range(self) -> None:
        low, high = _range([0.001], 0.001, 0.95)
        assert high > low
        assert (high - low) < 0.10, f"High-coverage should be narrow. Got width={(high - low):.4f}"

    def test_large_signal_low_coverage_wide_range(self) -> None:
        low, high = _range([0.40], 0.40, 0.10)
        assert (high - low) > 0.10

    def test_full_coverage_zero_widen(self) -> None:
        low, high = _range([0.20], 0.20, 1.0)
        assert low == pytest.approx(high, abs=0.001)

    def test_constants_are_set(self) -> None:
        assert MIN_COVERAGE_THRESHOLD == pytest.approx(0.20)
        assert BASE_UNCERTAINTY > 0
