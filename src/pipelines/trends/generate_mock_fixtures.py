"""Fixture generator for trend snapshots (mock_trends.json and per-date fixtures).

Eliminates hand-authored derived fields by computing velocity_fast,
direction_moderate, and direction_fast directly from score.py formulas:
  - velocity_fast = scenario_fast(velocity_moderate, automation_exposure)
  - direction_moderate = direction(velocity_moderate)
  - direction_fast = direction(velocity_fast)

Ensures labor_decay and labor_decay_source_note are synced with the
regenerated labor_decay.csv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipelines.trends.score import (  # noqa: E402
    direction,
    load_labor_decay,
    scenario_fast,
)

SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
CANONICAL_CSV = SEED_DIR / "canonical_skills.csv"

# Input base items for the 29 curated skills (defining base velocity_moderate and research_velocity)
BASE_ITEMS = [
    {
        "skill_id": "prompt-engineering",
        "skill_label": "Prompt engineering",
        "research_velocity": 0.48,
        "automation_exposure": 0.20,
        "velocity_moderate": 0.29,
    },
    {
        "skill_id": "llm-fine-tuning",
        "skill_label": "LLM fine-tuning & adaptation",
        "research_velocity": 0.55,
        "automation_exposure": 0.40,
        "velocity_moderate": 0.34,
    },
    {
        "skill_id": "rag-systems",
        "skill_label": "Retrieval-augmented generation (RAG)",
        "research_velocity": 0.60,
        "automation_exposure": 0.35,
        "velocity_moderate": 0.37,
    },
    {
        "skill_id": "ai-literacy",
        "skill_label": "AI literacy & tool fluency",
        "research_velocity": 0.42,
        "automation_exposure": 0.15,
        "velocity_moderate": 0.26,
    },
    {
        "skill_id": "ai-safety",
        "skill_label": "AI safety & alignment auditing",
        "research_velocity": 0.52,
        "automation_exposure": 0.12,
        "velocity_moderate": 0.32,
    },
    {
        "skill_id": "explainable-ai",
        "skill_label": "Explainable AI (XAI) & model interpretability",
        "research_velocity": 0.35,
        "automation_exposure": 0.18,
        "velocity_moderate": 0.22,
    },
    {
        "skill_id": "mlops",
        "skill_label": "MLOps & model deployment",
        "research_velocity": 0.48,
        "automation_exposure": 0.42,
        "velocity_moderate": 0.29,
    },
    {
        "skill_id": "vector-databases",
        "skill_label": "Vector database management & indexing",
        "research_velocity": 0.45,
        "automation_exposure": 0.38,
        "velocity_moderate": 0.28,
    },
    {
        "skill_id": "causal-inference",
        "skill_label": "Causal AI & counterfactual modeling",
        "research_velocity": 0.25,
        "automation_exposure": 0.32,
        "velocity_moderate": 0.16,
    },
    {
        "skill_id": "security-ai",
        "skill_label": "Adversarial robustness & AI security",
        "research_velocity": 0.40,
        "automation_exposure": 0.30,
        "velocity_moderate": 0.25,
    },
    {
        "skill_id": "manual-data-entry",
        "skill_label": "Manual data entry & typing",
        "research_velocity": -0.30,
        "automation_exposure": 0.88,
        "velocity_moderate": -0.19,
    },
    {
        "skill_id": "bookkeeping",
        "skill_label": "Bookkeeping & accounts payable/receivable",
        "research_velocity": -0.25,
        "automation_exposure": 0.82,
        "velocity_moderate": -0.16,
    },
    {
        "skill_id": "payroll-processing",
        "skill_label": "Payroll calculation & processing",
        "research_velocity": -0.22,
        "automation_exposure": 0.80,
        "velocity_moderate": -0.14,
    },
    {
        "skill_id": "document-filing",
        "skill_label": "Document sorting, filing & scanning",
        "research_velocity": -0.28,
        "automation_exposure": 0.85,
        "velocity_moderate": -0.17,
    },
    {
        "skill_id": "call-centre-scripted",
        "skill_label": "First-line customer support (scripted)",
        "research_velocity": -0.18,
        "automation_exposure": 0.80,
        "velocity_moderate": -0.11,
    },
    {
        "skill_id": "claims-processing",
        "skill_label": "Standard claims verification & logging",
        "research_velocity": -0.20,
        "automation_exposure": 0.83,
        "velocity_moderate": -0.12,
    },
    {
        "skill_id": "bank-reconciliation",
        "skill_label": "Bank reconciliation & statement matching",
        "research_velocity": -0.24,
        "automation_exposure": 0.81,
        "velocity_moderate": -0.15,
    },
    {
        "skill_id": "trade-confirmation",
        "skill_label": "Trade confirmation & settlement (back-office)",
        "research_velocity": -0.15,
        "automation_exposure": 0.82,
        "velocity_moderate": -0.09,
    },
    {
        "skill_id": "risk-compliance",
        "skill_label": "Regulatory compliance & reporting",
        "research_velocity": 0.10,
        "automation_exposure": 0.22,
        "velocity_moderate": 0.06,
    },
    {
        "skill_id": "audit-internal",
        "skill_label": "Internal audit & control testing",
        "research_velocity": 0.08,
        "automation_exposure": 0.25,
        "velocity_moderate": 0.05,
    },
    {
        "skill_id": "python",
        "skill_label": "Python programming",
        "research_velocity": 0.12,
        "automation_exposure": 0.48,
        "velocity_moderate": 0.09,
    },
    {
        "skill_id": "data-visualisation",
        "skill_label": "Data visualisation & reporting",
        "research_velocity": 0.12,
        "automation_exposure": 0.42,
        "velocity_moderate": 0.08,
    },
    {
        "skill_id": "financial-analysis",
        "skill_label": "Financial modelling & variance analysis",
        "research_velocity": 0.05,
        "automation_exposure": 0.44,
        "velocity_moderate": 0.03,
    },
    {
        "skill_id": "stakeholder-management",
        "skill_label": "Stakeholder communication & diplomacy",
        "research_velocity": 0.02,
        "automation_exposure": 0.18,
        "velocity_moderate": 0.02,
    },
    {
        "skill_id": "critical-thinking",
        "skill_label": "Critical thinking & complex problem solving",
        "research_velocity": 0.06,
        "automation_exposure": 0.12,
        "velocity_moderate": 0.04,
    },
    {
        "skill_id": "change-management",
        "skill_label": "Change management & organisational design",
        "research_velocity": 0.03,
        "automation_exposure": 0.15,
        "velocity_moderate": 0.02,
    },
    {
        "skill_id": "coaching-mentoring",
        "skill_label": "Coaching, mentoring & team leadership",
        "research_velocity": 0.05,
        "automation_exposure": 0.12,
        "velocity_moderate": 0.03,
    },
    {
        "skill_id": "process-mapping",
        "skill_label": "Business process mapping & re-engineering",
        "research_velocity": 0.09,
        "automation_exposure": 0.38,
        "velocity_moderate": 0.06,
    },
    {
        "skill_id": "cybersecurity-governance",
        "skill_label": "Cybersecurity governance & policy",
        "research_velocity": 0.22,
        "automation_exposure": 0.20,
        "velocity_moderate": 0.15,
    },
]


def build_fixture_for_date(
    snapshot_date: str,
    available_snapshots: list[str],
    labor_decay_map: dict[str, tuple[float, str]],
    is_baseline: bool,
    data_provenance_note: str,
) -> dict:
    """Build a complete, formula-consistent snapshot fixture."""
    items = []
    for base in BASE_ITEMS:
        sid = base["skill_id"]
        ld, ld_note = labor_decay_map.get(sid, (0.0, "no BLS mapping"))
        exposure = float(base["automation_exposure"])

        if is_baseline:
            # Baseline window (W42->W42): research_velocity is 0.0
            rv = 0.0
            v_mod = round(0.4 * ld, 6)
        else:
            rv = float(base["research_velocity"])
            v_mod = float(base["velocity_moderate"])

        # Derived fields computed strictly via score.py formulas
        v_fast = round(scenario_fast(v_mod, exposure), 6)
        dir_mod = direction(v_mod)
        dir_fast = direction(v_fast)

        items.append(
            {
                "skill_id": sid,
                "skill_label": base["skill_label"],
                "research_velocity": rv,
                "labor_decay": ld,
                "labor_decay_source_note": ld_note,
                "automation_exposure": exposure,
                "velocity_moderate": v_mod,
                "velocity_fast": v_fast,
                "direction_moderate": dir_mod,
                "direction_fast": dir_fast,
            }
        )

    return {
        "meta": {
            "sources": [
                {
                    "name": "arXiv cs.AI RSS",
                    "url": "https://rss.arxiv.org/rss/cs.AI",
                    "retrieved_at": snapshot_date,
                },
                {
                    "name": "BLS Occupational Projections 2023-2033",
                    "url": (
                        "https://www.bls.gov/emp/tables/"
                        "occupational-projections-and-characteristics.htm"
                    ),
                    "retrieved_at": snapshot_date,
                },
            ],
            "snapshot_date": snapshot_date,
            "scenario": "moderate",
            "is_estimate": True,
            "weights": {"research_velocity": 0.6, "labor_decay": 0.4},
            "labor_decay_is_static": True,
            "available_snapshots": available_snapshots,
            "data_provenance_note": data_provenance_note,
        },
        "items": items,
    }


def generate_all() -> None:
    available = ["2026-10-13", "2026-10-20"]
    ld_map = load_labor_decay()

    # 1. Baseline snapshot: 2026-10-13
    fixture_w42 = build_fixture_for_date(
        snapshot_date="2026-10-13",
        available_snapshots=available,
        labor_decay_map=ld_map,
        is_baseline=True,
        data_provenance_note=(
            "Baseline snapshot calibrated from arXiv cs.AI query API "
            "(window 2024-10-06 to 2024-10-12) to 2026-W42."
        ),
    )
    file_w42 = SEED_DIR / "mock_trends_2026-10-13.json"
    with file_w42.open("w", encoding="utf-8") as fh:
        json.dump(fixture_w42, fh, indent=2, ensure_ascii=False)
    print(f"Generated {file_w42} ({len(fixture_w42['items'])} items)")

    # 2. Delta snapshot: 2026-10-20
    fixture_w43 = build_fixture_for_date(
        snapshot_date="2026-10-20",
        available_snapshots=available,
        labor_decay_map=ld_map,
        is_baseline=False,
        data_provenance_note=(
            "Delta snapshot measuring week-over-week change from arXiv cs.AI "
            "query API windows (2024-10-13..2024-10-19 vs 2024-10-06..2024-10-12)."
        ),
    )
    file_w43 = SEED_DIR / "mock_trends_2026-10-20.json"
    with file_w43.open("w", encoding="utf-8") as fh:
        json.dump(fixture_w43, fh, indent=2, ensure_ascii=False)
    print(f"Generated {file_w43} ({len(fixture_w43['items'])} items)")

    # 3. Default mock_trends.json (alias of latest snapshot)
    file_default = SEED_DIR / "mock_trends.json"
    with file_default.open("w", encoding="utf-8") as fh:
        json.dump(fixture_w43, fh, indent=2, ensure_ascii=False)
    print(f"Generated {file_default} ({len(fixture_w43['items'])} items)")


if __name__ == "__main__":
    generate_all()
