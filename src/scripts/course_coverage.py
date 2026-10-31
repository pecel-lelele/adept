"""Weighted course-coverage audit for target roles (issue #84, M3-042/M3-045).

For each target role: uncovered share = sum of importance of requirements whose skill is
offered by no catalogue course / sum of importance of all its requirements. Uses the same
production loaders as the pathway engine, so it reads the seed CSVs and canonical skill IDs.

Run from the repository root:
    uv run --frozen python src/scripts/course_coverage.py --out report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
os.environ["M3_BACKEND"] = "csv"  # audit the committed seed files, not a local database

from app.core import taxonomy  # noqa: E402
from app.features.pathway import data  # noqa: E402


def audit() -> dict[str, object]:
    offered = {taxonomy.canonical(s) for c in data.catalogue() for s in c.skill_ids}
    roles: dict[str, dict[str, object]] = {}
    for role in data.target_role_ids():
        reqs = data.requirements(role)
        total = sum(r.importance for r in reqs)
        missing = [r for r in reqs if taxonomy.canonical(r.skill_id) not in offered]
        weight = sum(r.importance for r in missing)
        roles[role] = {
            "total_importance": round(total, 4),
            "uncovered_importance": round(weight, 4),
            "uncovered_share": round(weight / total, 4) if total else 0.0,
            "uncovered_skills": sorted(r.skill_id for r in missing),
        }
    with_gap = [r for r, v in roles.items() if v["uncovered_skills"]]
    return {"target_roles": len(roles), "roles_with_gap": len(with_gap), "roles": roles}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(f"{report['roles_with_gap']}/{report['target_roles']} target roles have a course gap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
