"""Offline KPI calculation from anonymous, synthetic-case stopwatch records.

No database, environment, application imports, network or third-party dependencies.
Usage: python src/scripts/kpi_time_to_plan.py trials.json
       python src/scripts/kpi_time_to_plan.py --template > trials.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections.abc import Sequence
from pathlib import Path

CASES = ("imran", "sofia", "meera", "adrian", "nur-hana")
WORKFLOWS = ("manual", "adept")


def template() -> list[dict[str, object]]:
    return [
        {
            "tester": f"T{tester}",
            "case": case,
            "workflow": workflow,
            "elapsed_seconds": None,
            "valid": False,
            "status": "not_run",
        }
        for tester in range(1, 4)
        for case in CASES
        for workflow in WORKFLOWS
    ]


def median_minutes(seconds: Sequence[float]) -> float | None:
    return statistics.median(seconds) / 60 if seconds else None


def analyse(value: object) -> dict[str, object]:
    if not isinstance(value, list):
        raise ValueError("Expected a JSON array of trial records")
    rows: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict) or set(row) != {
            "tester",
            "case",
            "workflow",
            "elapsed_seconds",
            "valid",
            "status",
        }:
            raise ValueError("Trial fields must match the template exactly; omit personal data")
        tester, case, workflow = row["tester"], row["case"], row["workflow"]
        if (
            not all(isinstance(v, str) for v in (tester, case, workflow))
            or tester not in {"T1", "T2", "T3"}
            or case not in CASES
            or workflow not in WORKFLOWS
        ):
            raise ValueError("Use the provided anonymous testers, synthetic cases and workflows")
        key = (str(tester), str(case), str(workflow))
        if key in rows:
            raise ValueError("Duplicate tester/case/workflow")
        if type(row["valid"]) is not bool:
            raise ValueError("valid must be a JSON boolean")
        status, elapsed = row["status"], row["elapsed_seconds"]
        if not isinstance(status, str) or status not in {"not_run", "completed", "failed"}:
            raise ValueError("Unknown trial status")
        if elapsed is not None and (
            type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0
        ):
            raise ValueError("Elapsed seconds must be positive and finite")
        if status == "completed" and elapsed is None:
            raise ValueError("Completed trials require a duration")
        if status == "not_run" and elapsed is not None:
            raise ValueError("Unrun trials cannot have a duration")
        if row["valid"] and status != "completed":
            raise ValueError("Only completed, reviewed plans can be valid")
        rows[key] = row

    groups: dict[str, object] = {}
    for workflow in WORKFLOWS:
        group = [r for key, r in rows.items() if key[2] == workflow]
        attempted = [r for r in group if r["status"] != "not_run"]
        valid = [r for r in attempted if r["valid"]]
        times = [float(str(r["elapsed_seconds"])) for r in valid]
        groups[workflow] = {
            "n_records": len(group),
            "n_attempted": len(attempted),
            "n_not_run": sum(r["status"] == "not_run" for r in group),
            "n_failed": sum(r["status"] == "failed" for r in group),
            "n_valid": len(valid),
            "valid_plan_percent": 100 * len(valid) / len(attempted) if attempted else None,
            "median_valid_plan_minutes": median_minutes(times),
        }

    manual_times: list[float] = []
    adept_times: list[float] = []
    for tester in ("T1", "T2", "T3"):
        for case in CASES:
            manual, adept = rows.get((tester, case, "manual")), rows.get((tester, case, "adept"))
            if manual and adept and manual["valid"] and adept["valid"]:
                manual_times.append(float(str(manual["elapsed_seconds"])))
                adept_times.append(float(str(adept["elapsed_seconds"])))
    baseline, assisted = median_minutes(manual_times), median_minutes(adept_times)
    reduction = (
        100 * (baseline - assisted) / baseline
        if baseline is not None and assisted is not None
        else None
    )
    return {
        "workflows": groups,
        "paired_valid_n": len(manual_times),
        "paired_manual_median_minutes": baseline,
        "paired_adept_median_minutes": assisted,
        "paired_median_reduction_percent": reduction,
        "expected_records": 30,
        "missing_records": 30 - len(rows),
        "all_pairs_valid": len(manual_times) == 15,
        "interpretation": (
            "Descriptive synthetic-case results only. "
            "Compare validity and failures alongside time. "
            "No automatic pass/fail or population impact claim; reviewer validity is not inferred."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    if args.template:
        if args.input:
            parser.error("Use --template without an input file")
        result: object = template()
    else:
        if args.input is None:
            parser.error("Provide a trial JSON file or --template")
        try:
            result = analyse(json.loads(args.input.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
