"""Evaluation harness and benchmark tests for role matching (M2-09, M2-10).

Validates:
1. Correctness of IR ranking metrics (Precision@k, Recall@k, MRR, nDCG@k).
2. Offline ranking benchmark over synthetic personas (Aisyah, Wei Jie, Ravi)
   against ground-truth expected future roles from `expected_roles.csv`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

# pyrefly: ignore[missing-import]
from app.features.matching.evaluation import (  # type: ignore
    aggregate_benchmark,
    evaluate_ranking,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

# pyrefly: ignore[missing-import]
from app.features.matching.scoring import (  # type: ignore
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    rank_roles,
)

SEED_DIR = Path(__file__).resolve().parents[3] / "src" / "data" / "seed"


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


def _load_expected_roles() -> dict[str, dict[str, float]]:
    path = SEED_DIR / "personas" / "expected_roles.csv"
    gt: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["user_id"]
            if uid not in gt:
                gt[uid] = {}
            gt[uid][row["role_id"]] = float(row["relevance"])
    return gt


def _load_catalog_roles() -> list[Role]:
    """Build Role objects from taxonomy seed files (roles.csv, role_skills.csv)."""
    skills_by_role: dict[str, list[RoleSkill]] = {}
    rs_path = SEED_DIR / "taxonomy" / "role_skills.csv"
    with open(rs_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            skills_by_role.setdefault(row["role_id"], []).append(
                RoleSkill(
                    skill_id=row["skill_id"],
                    importance=float(row["importance"]),
                )
            )

    interest_map = {
        "process-automation-analyst": frozenset(
            {"process improvement", "operations", "automation", "finance"}
        ),
        "data-analyst": frozenset({"data", "analytics", "software"}),
        "compliance-analytics-officer": frozenset({"finance", "risk", "data", "compliance"}),
        "ai-operations-specialist": frozenset({"software", "AI", "automation"}),
    }

    roles: list[Role] = []
    for role_id, skills in skills_by_role.items():
        roles.append(
            Role(
                role_id=role_id,
                skills=tuple(skills),
                interest_tags=interest_map.get(role_id, frozenset()),
            )
        )
    return roles


def _load_personas() -> dict[str, MatchProfile]:
    """Build MatchProfile objects from personas seed data (user_skills.csv, profiles.csv)."""
    # 1. Interests from profiles.csv
    interests: dict[str, set[str]] = {}
    with open(SEED_DIR / "personas" / "profiles.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row["interests"].strip("{}")
            tags = {t.strip() for t in raw.split(",") if t.strip()}
            interests[row["user_id"]] = tags

    # 2. Skills from user_skills.csv (convert level 1-5 to float 0..1)
    skills: dict[str, dict[str, float]] = {}
    with open(SEED_DIR / "personas" / "user_skills.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lvl = int(row["level"])
            norm = (lvl - 1) / 4.0  # 1->0.0, 3->0.5, 5->1.0
            skills.setdefault(row["user_id"], {})[row["skill_id"]] = norm

    return {
        uid: MatchProfile(
            skills=skills.get(uid, {}),
            interests=frozenset(interests.get(uid, set())),
        )
        for uid in ("aisyah", "weijie", "ravi")
    }


def test_synthetic_personas_evaluation_benchmark() -> None:
    """Benchmark matching engine against hand-labelled ground truth (M2-09).

    Asserts that precision@3, recall@3, and nDCG@3 exceed quality thresholds
    across all synthetic personas.
    """
    expected = _load_expected_roles()
    personas = _load_personas()
    roles = _load_catalog_roles()

    # Canonical baseline velocities
    velocities = {
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

    results = []
    for user_id, profile in personas.items():
        ranked_scores = rank_roles(
            profile, roles, velocities, Weights(skill=0.5, trend=0.3, interest=0.2)
        )
        ranked_role_ids = [r.role_id for r in ranked_scores]

        metrics = evaluate_ranking(ranked_role_ids, expected[user_id], k=3)
        results.append(metrics)

        # Each persona's top recommendation should be an established relevant role (MRR == 1.0)
        assert metrics.reciprocal_rank == 1.0, (
            f"{user_id} top recommendation {ranked_role_ids[0]} not in ground truth"
        )
        # At least 2 of top 3 must be relevant
        assert metrics.precision_at_k >= 0.66, (
            f"{user_id} Precision@3 too low: {metrics.precision_at_k}"
        )

    summary = aggregate_benchmark(results)

    # Benchmark acceptance gates
    assert summary.mean_mrr == 1.0
    assert summary.mean_precision_at_k >= 0.85
    assert summary.mean_recall_at_k >= 0.85
    assert summary.mean_ndcg_at_k >= 0.90
