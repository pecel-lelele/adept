"""tests/pipelines/trends/test_score.py

Unit tests for the pure scoring functions in src/pipelines/trends/score.py.
No DB, no network, no ML model needed.

Coverage:
  - RV sign correctness for rising vs falling frequency
  - Fast-scenario amplification for both V<0 and V>=0 branches
  - Clamp behavior at the [-2.0, 2.0] boundary
  - direction() thresholds
  - composite_velocity weights
"""

import math

import pytest

from pipelines.trends.score import (
    EPS,
    V_CLAMP_MAX,
    V_CLAMP_MIN,
    K,
    clamp,
    composite_velocity,
    direction,
    research_velocity,
    scenario_fast,
)

# ---------------------------------------------------------------------------
# research_velocity (RV)
# ---------------------------------------------------------------------------


class TestResearchVelocity:
    def test_rising_frequency_positive_rv(self) -> None:
        """When mention frequency grows, RV must be positive."""
        rv = research_velocity(freq_t0=0.05, freq_t1=0.10)
        assert rv > 0, f"Expected RV > 0 for rising frequency, got {rv}"

    def test_falling_frequency_negative_rv(self) -> None:
        """When mention frequency falls, RV must be negative."""
        rv = research_velocity(freq_t0=0.10, freq_t1=0.05)
        assert rv < 0, f"Expected RV < 0 for falling frequency, got {rv}"

    def test_stable_frequency_zero_rv(self) -> None:
        """When frequency is unchanged, RV must be 0."""
        rv = research_velocity(freq_t0=0.08, freq_t1=0.08)
        assert rv == pytest.approx(0.0, abs=1e-9)

    def test_zero_freq_uses_epsilon(self) -> None:
        """Zero frequencies are handled via eps; result must be finite."""
        rv = research_velocity(freq_t0=0.0, freq_t1=0.0)
        assert math.isfinite(rv)
        assert rv == pytest.approx(0.0, abs=1e-9)

    def test_rv_formula_matches_manual(self) -> None:
        """RV = ln((freq_t1 + eps) / (freq_t0 + eps))."""
        f0, f1 = 0.05, 0.10
        expected = math.log((f1 + EPS) / (f0 + EPS))
        assert research_velocity(f0, f1) == pytest.approx(expected, rel=1e-9)

    def test_large_growth_produces_large_positive(self) -> None:
        rv = research_velocity(freq_t0=0.001, freq_t1=0.20)
        assert rv > 1.0


# ---------------------------------------------------------------------------
# composite_velocity weights
# ---------------------------------------------------------------------------


class TestCompositeVelocity:
    def test_weights_sum_correctly(self) -> None:
        """V = 0.6*RV + 0.4*labor_decay."""
        rv = 0.5
        ld = -0.1
        expected = 0.6 * rv + 0.4 * ld
        assert composite_velocity(rv, ld) == pytest.approx(expected, rel=1e-9)

    def test_positive_when_rv_dominates(self) -> None:
        assert composite_velocity(rv=0.5, labor_decay=-0.01) > 0

    def test_negative_when_labor_decay_dominates(self) -> None:
        assert composite_velocity(rv=-0.5, labor_decay=-0.3) < 0


# ---------------------------------------------------------------------------
# scenario_fast amplification
# ---------------------------------------------------------------------------


class TestScenarioFast:
    def test_negative_v_amplified_by_exposure(self) -> None:
        """V < 0: V_fast = V * (1 + E * k), so |V_fast| > |V| for E > 0."""
        v = -0.20
        exposure = 0.80
        v_fast = scenario_fast(v, exposure)
        # |v_fast| should be larger than |v|
        assert abs(v_fast) > abs(v), f"Fast scenario should amplify decline: v={v}, v_fast={v_fast}"

    def test_negative_v_formula_matches(self) -> None:
        """V_fast = V * (1 + E * k), unclamped range."""
        v = -0.20
        exposure = 0.80
        expected_unclamped = v * (1 + exposure * K)
        expected = max(V_CLAMP_MIN, min(V_CLAMP_MAX, expected_unclamped))
        assert scenario_fast(v, exposure) == pytest.approx(expected, rel=1e-9)

    def test_positive_v_amplified_by_low_exposure(self) -> None:
        """V >= 0: V_fast = V * (1 + (1-E) * k), amplifies rising skills with low exposure."""
        v = 0.20
        exposure = 0.10  # low automation exposure → rising skill gains more
        v_fast = scenario_fast(v, exposure)
        assert v_fast > v, (
            f"Fast scenario should amplify rising low-exposure skill: v={v}, v_fast={v_fast}"
        )

    def test_positive_v_formula_matches(self) -> None:
        """V_fast = V * (1 + (1-E) * k), unclamped."""
        v = 0.20
        exposure = 0.20
        expected_unclamped = v * (1 + (1 - exposure) * K)
        expected = max(V_CLAMP_MIN, min(V_CLAMP_MAX, expected_unclamped))
        assert scenario_fast(v, exposure) == pytest.approx(expected, rel=1e-9)

    def test_clamp_lower_bound(self) -> None:
        """Result must never go below -2.0."""
        v_fast = scenario_fast(v=-1.5, automation_exposure=0.90)
        assert v_fast >= V_CLAMP_MIN, f"Expected >= {V_CLAMP_MIN}, got {v_fast}"

    def test_clamp_upper_bound(self) -> None:
        """Result must never exceed +2.0."""
        v_fast = scenario_fast(v=1.5, automation_exposure=0.05)
        assert v_fast <= V_CLAMP_MAX, f"Expected <= {V_CLAMP_MAX}, got {v_fast}"

    def test_clamp_exactly_at_boundary(self) -> None:
        """Force a value past the boundary and confirm clamp to exactly ±2."""
        # V=2.0, exposure=0.0 → V_fast = 2*(1 + 1.0 * 1.5) = 5.0 → clamped to 2.0
        v_fast = scenario_fast(v=2.0, automation_exposure=0.0)
        assert v_fast == V_CLAMP_MAX

        # V=-2.0, exposure=1.0 → V_fast = -2*(1 + 1.0*1.5) = -5.0 → clamped to -2.0
        v_fast = scenario_fast(v=-2.0, automation_exposure=1.0)
        assert v_fast == V_CLAMP_MIN

    def test_zero_v_stays_zero(self) -> None:
        """V=0: both branches multiply 0, result stays 0."""
        assert scenario_fast(v=0.0, automation_exposure=0.5) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# direction thresholds
# ---------------------------------------------------------------------------


class TestDirection:
    def test_rising(self) -> None:
        assert direction(0.06) == "rising"
        assert direction(1.0) == "rising"

    def test_declining(self) -> None:
        assert direction(-0.06) == "declining"
        assert direction(-1.0) == "declining"

    def test_stable(self) -> None:
        assert direction(0.00) == "stable"
        assert direction(0.05) == "stable"  # exactly at boundary → stable
        assert direction(-0.05) == "stable"  # exactly at boundary → stable
        assert direction(0.04) == "stable"

    def test_boundary_above_rise(self) -> None:
        """Just above 0.05 → rising."""
        assert direction(0.051) == "rising"

    def test_boundary_below_decline(self) -> None:
        """Just below -0.05 → declining."""
        assert direction(-0.051) == "declining"


# ---------------------------------------------------------------------------
# clamp helper
# ---------------------------------------------------------------------------


class TestClamp:
    def test_within_range(self) -> None:
        assert clamp(0.5, -2.0, 2.0) == 0.5

    def test_below_min(self) -> None:
        assert clamp(-3.0, -2.0, 2.0) == -2.0

    def test_above_max(self) -> None:
        assert clamp(5.0, -2.0, 2.0) == 2.0

    def test_at_min(self) -> None:
        assert clamp(-2.0, -2.0, 2.0) == -2.0

    def test_at_max(self) -> None:
        assert clamp(2.0, -2.0, 2.0) == 2.0


# ---------------------------------------------------------------------------
# Signal aggregation across multiple pulls in same period
# ---------------------------------------------------------------------------


class TestSignalAggregation:
    def test_two_same_week_pulls_aggregate_both_count_and_total(self) -> None:
        """Simulates two same-week pulls of (10 mentions, 100 papers) each.
        Asserts frequency is 20/200 = 0.10, not 10/200 (overwritten count) or 10/100."""
        from pipelines.trends.score import aggregate_period_runs

        pull1 = ({"python": 10.0, "sql": 5.0}, 100)
        pull2 = ({"python": 10.0, "sql": 5.0}, 100)

        combined_counts, combined_total = aggregate_period_runs([pull1, pull2])

        assert combined_total == 200, f"Expected 200 total papers, got {combined_total}"
        assert combined_counts["python"] == 20.0, (
            f"Expected 20 mentions for python, got {combined_counts['python']}"
        )
        assert combined_counts["sql"] == 10.0

        freq_python = combined_counts["python"] / combined_total
        assert freq_python == pytest.approx(0.10, abs=1e-9)
