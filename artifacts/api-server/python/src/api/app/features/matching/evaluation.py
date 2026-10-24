"""Evaluation metrics and offline validation harness for role matching (M2-09).

Computes ranking quality metrics (Precision@k, Recall@k, MRR, nDCG@k)
over synthetic personas against ground-truth relevant roles.
All functions are pure and testable without database or network I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RankingMetrics:
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    k: int


def precision_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Proportion of top-k recommended items that are relevant."""
    if k <= 0 or not recommended:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k


def recall_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Proportion of truly relevant items that appear in top-k recommendations."""
    if not relevant or k <= 0:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def reciprocal_rank(recommended: list[str], relevant: set[str]) -> float:
    """1 / rank of the first relevant item in the recommended list (1-indexed)."""
    for idx, item in enumerate(recommended):
        if item in relevant:
            return 1.0 / (idx + 1)
    return 0.0


def dcg_at_k(recommended: list[str], relevance: dict[str, float], k: int) -> float:
    """Discounted Cumulative Gain at rank k using standard log2 discounting:

    DCG@k = sum_{i=1}^k (rel_i / log2(i + 1))
    """
    if k <= 0:
        return 0.0
    score = 0.0
    for idx, item in enumerate(recommended[:k]):
        rel = relevance.get(item, 0.0)
        if rel > 0:
            score += rel / math.log2(idx + 2)  # idx 0 -> log2(2) = 1.0
    return score


def ndcg_at_k(recommended: list[str], relevance: dict[str, float], k: int) -> float:
    """Normalized Discounted Cumulative Gain at rank k (0..1).

    Compares DCG@k against the Ideal DCG@k (IDCG) from a perfect descending sort.
    """
    if k <= 0:
        return 0.0
    actual_dcg = dcg_at_k(recommended, relevance, k)
    if actual_dcg == 0.0:
        return 0.0

    # Ideal ranking sorts all available relevance scores in descending order
    ideal_order = sorted(relevance.keys(), key=lambda r: relevance[r], reverse=True)
    ideal_dcg = dcg_at_k(ideal_order, relevance, k)

    if ideal_dcg == 0.0:
        return 0.0
    return min(max(actual_dcg / ideal_dcg, 0.0), 1.0)


def evaluate_ranking(
    recommended: list[str],
    ground_truth_relevance: dict[str, float],
    k: int = 3,
) -> RankingMetrics:
    """Evaluate a single ranking against ground-truth graded relevance.

    Items with relevance > 0 are considered relevant for binary metrics.
    """
    relevant_set = {item for item, rel in ground_truth_relevance.items() if rel > 0}
    p_k = precision_at_k(recommended, relevant_set, k)
    r_k = recall_at_k(recommended, relevant_set, k)
    rr = reciprocal_rank(recommended, relevant_set)
    ndcg = ndcg_at_k(recommended, ground_truth_relevance, k)

    return RankingMetrics(
        precision_at_k=round(p_k, 4),
        recall_at_k=round(r_k, 4),
        reciprocal_rank=round(rr, 4),
        ndcg_at_k=round(ndcg, 4),
        k=k,
    )


@dataclass(frozen=True)
class BenchmarkSummary:
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_mrr: float
    mean_ndcg_at_k: float
    persona_count: int
    k: int


def aggregate_benchmark(results: list[RankingMetrics]) -> BenchmarkSummary:
    """Calculate average metrics across all evaluated personas."""
    n = len(results)
    if n == 0:
        return BenchmarkSummary(0.0, 0.0, 0.0, 0.0, 0, 0)

    k = results[0].k
    return BenchmarkSummary(
        mean_precision_at_k=round(sum(r.precision_at_k for r in results) / n, 4),
        mean_recall_at_k=round(sum(r.recall_at_k for r in results) / n, 4),
        mean_mrr=round(sum(r.reciprocal_rank for r in results) / n, 4),
        mean_ndcg_at_k=round(sum(r.ndcg_at_k for r in results) / n, 4),
        persona_count=n,
        k=k,
    )
