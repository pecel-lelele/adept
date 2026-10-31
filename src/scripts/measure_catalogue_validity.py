"""Measure the Phase 1 catalogue-ID validity KPI with the production pathway engine.

validity = 100 * recommended course IDs found in the catalogue / all recommended course IDs

Writes docs/evidence/catalogue-id-validity.json. Synthetic personas only; no model or paid call.
Usage: python src/scripts/measure_catalogue_validity.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "api"))
OUT = ROOT / "docs" / "evidence" / "catalogue-id-validity.json"
CATALOGUE = ROOT / "src" / "data" / "seed" / "courses" / "courses.csv"
SCENARIOS = ("moderate", "fast")


def validity_percent(valid: int, recommended: int) -> float | None:
    return round(100 * valid / recommended, 2) if recommended else None


def main() -> None:
    os.environ.update(LLM_PROVIDER="none", EMBEDDINGS_PROVIDER="none", M3_BACKEND="csv")
    os.environ["DATABASE_URL"] = ""

    from app.features.impact import service as impact
    from app.features.pathway import engine
    from app.features.pathway import service as pathway

    with CATALOGUE.open(encoding="utf-8", newline="") as handle:
        catalogue = {row["id"] for row in csv.DictReader(handle)}
    summary = impact.compute_summary()
    tops = {p.persona_id: p for p in summary.personas}
    records = []
    for persona in impact.load_personas():
        learner = engine.Learner(
            persona.skills, persona.hours_per_week, persona.budget_myr, persona.hrd_eligible
        )
        for scenario in SCENARIOS:
            role = getattr(tops[persona.persona_id], scenario).top_role_id
            courses = impact.path_courses(pathway.build_pathway(learner, role, scenario))
            records.append(
                {
                    "persona": persona.persona_id,
                    "scenario": scenario,
                    "role": role,
                    "recommended": len(courses),
                    "valid": sum(course.id in catalogue for course in courses),
                }
            )
    recommended = sum(r["recommended"] for r in records)
    valid = sum(r["valid"] for r in records)
    OUT.write_text(
        json.dumps(
            {
                "kpi": "catalogue-ID validity",
                "formula": "100 * valid course IDs / recommended course IDs",
                "target_percent": 100,
                "personas": len(tops),
                "scenarios": list(SCENARIOS),
                "catalogue_courses": len(catalogue),
                "recommended": recommended,
                "valid": valid,
                "validity_percent": validity_percent(valid, recommended),
                "limits": "ID resolution on synthetic personas; not a check of every price or link.",
                "records": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{valid}/{recommended} valid = {validity_percent(valid, recommended)}%")


if __name__ == "__main__":
    main()
