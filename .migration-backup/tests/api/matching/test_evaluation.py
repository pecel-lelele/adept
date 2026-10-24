"""Evaluation harness and benchmark tests for role matching (M2-09, M2-10).

Validates:
1. Correctness of IR ranking metrics (Precision@k, Recall@k, MRR, nDCG@k).
2. Offline ranking benchmark over synthetic personas (Aisyah, Wei Jie, Ravi)
   against ground-truth expected future roles from `expected_roles.csv`.

The benchmark must not carry its own copy of production data or logic:
catalog roles come from ``repository.load_roles`` (role interest tags via the
production getter), personas and ground truth come from ``personas.py`` (the
harness loader), and scoring comes from ``scoring.rank_roles``.
"""

from __future__ import annotations

import pytest

# pyrefly: ignore[missing-import]
from app.features.matching import repository
from app.features.matching.evaluation import (  # type: ignore
    BenchmarkSummary,
    RankingMetrics,
    aggregate_benchmark,
    evaluate_ranking,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

# pyrefly: ignore[missing-import]
from app.features.matching.personas import load_all_personas, load_expected_roles

# pyrefly: ignore[missing-import]
from app.features.matching.scoring import Weights, rank_roles

K = 3
_WEIGHTS = Weights()  # production defaults (M2-011) — the benchmark must score with them

# Canonical baseline velocities for the offline benchmark.  These are frozen
# benchmark inputs (ground-truth-adjacent data, like expected_roles.csv), not a
# copy of production logic; production velocities come from M1's live snapshot
# via trend_port and would make the benchmark drift with M1 data.
_BASELINE_VELOCITIES = {
    "python": 0.05,
    "sql": 0.03,
    "data-visualisation": 0.02,
    "rpa": 0.04,
    "prompt-engineering": 0.04,
    "ai-literacy": 0.03,
    "process-mapping": 0.01,
    "risk-compliance": 0.02,
    "excel": 0.01,
}


# ---------------------------------------------------------------------------
# Unit tests for ranking metrics
# ---------------------------------------------------------------------------


def test_precision_at_k_calculation() -> None:
    rec = ["role-a", "role-b", "role-c", "role-d"]
    relevant = {"role-a", "role-c"}

    assert precision_at_k(rec, relevant, k=2) == 0.5  # 1 out of 2 (role-a)
    assert precision_at_k(rec, relevant, k=3) == pytest.approx(2 / 3)  # role-a, role-c
    assert precision_at_k(rec, relevant, k=0) == 0.0
    assert precision_at_k([], relevant, k=3) == 0.0


def test_recall_at_k_calculation() -> None:
    rec = ["role-a", "role-b", "role-c", "role-d"]
    relevant = {"role-a", "role-c", "role-e"}  # 3 total relevant

    assert recall_at_k(rec, relevant, k=1) == pytest.approx(1 / 3)  # role-a
    assert recall_at_k(rec, relevant, k=3) == pytest.approx(2 / 3)  # role-a, role-c
    assert recall_at_k(rec, set(), k=3) == 0.0


def test_reciprocal_rank_calculation() -> None:
    rec = ["role-a", "role-b", "role-c"]
    assert reciprocal_rank(rec, {"role-a"}) == 1.0
    assert reciprocal_rank(rec, {"role-b"}) == 0.5
    assert reciprocal_rank(rec, {"role-c"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(rec, {"role-missing"}) == 0.0


def test_dcg_and_ndcg_properties() -> None:
    relevance = {"role-a": 3.0, "role-b": 2.0, "role-c": 1.0}

    # Perfect ranking: IDCG == DCG -> nDCG == 1.0
    ideal = ["role-a", "role-b", "role-c"]
    assert ndcg_at_k(ideal, relevance, k=3) == pytest.approx(1.0)

    # Sub-optimal ranking should have strictly lower nDCG
    sub_optimal = ["role-c", "role-b", "role-a"]
    assert ndcg_at_k(sub_optimal, relevance, k=3) < 1.0
    assert ndcg_at_k(sub_optimal, relevance, k=3) > 0.0

    # Irrelevant recommendations yield 0.0
    zero_rel = ["role-x", "role-y"]
    assert ndcg_at_k(zero_rel, relevance, k=2) == 0.0


# ---------------------------------------------------------------------------
# Synthetic Persona Benchmark (M2-09, M2-10)
# ---------------------------------------------------------------------------


def _run_benchmark() -> tuple[list[RankingMetrics], BenchmarkSummary]:
    """Rank every synthetic persona with the production engine and score the ranking.

    Everything below comes from production code: catalog roles and interest
    tags from repository.load_roles(), personas and ground truth from the
    personas.py harness loader, scoring from scoring.rank_roles.
    """
    expected = load_expected_roles()
    personas = load_all_personas()
    roles = repository.load_roles()

    results: list[RankingMetrics] = []
    for user_id, profile in personas.items():
        ranked_role_ids = [
            r.role_id for r in rank_roles(profile, roles, _BASELINE_VELOCITIES, _WEIGHTS)
        ]
        results.append(evaluate_ranking(ranked_role_ids, expected[user_id], k=K))
    return results, aggregate_benchmark(results)


def _per_persona_report(results: list[RankingMetrics]) -> str:
    return "\n".join(
        f"  persona {i}: P@{m.k}={m.precision_at_k} R@{m.k}={m.recall_at_k} "
        f"MRR={m.reciprocal_rank} nDCG@{m.k}={m.ndcg_at_k}"
        for i, m in enumerate(results, 1)
    )


def test_synthetic_personas_evaluation_benchmark(capsys: pytest.CaptureFixture[str]) -> None:
    """Benchmark matching engine against hand-labelled ground truth (M2-09).

    Asserts that precision@3, recall@3, and nDCG@3 exceed quality thresholds
    across all synthetic personas.
    """
    results, summary = _run_benchmark()

    for metrics in results:
        # At least 2 of top 3 must be relevant
        assert metrics.precision_at_k >= 0.66, f"Precision@3 too low: {metrics.precision_at_k}"

    print("\n=== Matching benchmark (production code path) ===")
    print(_per_persona_report(results))
    print(
        f"  mean: P@3={summary.mean_precision_at_k} R@3={summary.mean_recall_at_k} "
        f"MRR={summary.mean_mrr} nDCG@3={summary.mean_ndcg_at_k} "
        f"(personas={summary.persona_count})"
    )

    # Benchmark acceptance gates
    assert summary.mean_mrr == 1.0
    assert summary.mean_precision_at_k >= 0.85
    assert summary.mean_recall_at_k >= 0.85
    assert summary.mean_ndcg_at_k >= 0.90


def test_benchmark_is_wired_to_production_role_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard (12b): patching production role tags must change the benchmark result.

    Proves the benchmark reads interest tags through repository, not a copy.
    """
    baseline_results, baseline_summary = _run_benchmark()

    real_getter = repository.role_interest_tags
    target = "compliance-analytics-officer"

    def patched_getter(role_id: str) -> frozenset[str]:
        if role_id == target:
            return frozenset()  # strip this role's interest tags
        return real_getter(role_id)

    monkeypatch.setattr(repository, "role_interest_tags", patched_getter)
    patched_results, patched_summary = _run_benchmark()

    assert any(r1 != r2 for r1, r2 in zip(baseline_results, patched_results, strict=True)), (
        "benchmark ranking did not change when production role tags were patched — "
        "the test is not wired to production code"
    )
    assert patched_summary != baseline_summary
