"""Measure isolated local API journeys; never human planning-time KPI evidence.

Run in a fresh process: python src/scripts/measure_synthetic_journeys.py --run-local-isolated
Only the five committed synthetic demo PDFs/profiles are read. No listening server,
database writes, external model calls, or real identities are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-local-isolated", action="store_true", required=True)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 11))
    args = parser.parse_args()
    # Override ambient configuration before importing any application module.
    os.environ.update(
        {
            "APP_ENV": "development",
            "M3_BACKEND": "csv",
            "AUTH_MODE": "demo",
            "DATABASE_URL": "postgresql://adept:adept@127.0.0.1:1/measurement_unreachable",
            "AUTH_RAW_USER_IDS": "false",
            "AUTH_DEFAULT_USER": "",
            "SESSION_SECRET": "isolated-synthetic-measurements-only",
            "LLM_PROVIDER": "none",
            "LLM_FALLBACK_PROVIDER": "",
            "LLM_API_KEY": "",
            "LLM_FALLBACK_API_KEY": "",
            "GEMINI_API_KEY": "",
            "RUNPOD_API_KEY": "",
            "TRENDS_RUNPOD_API_KEY": "",
            "TRENDS_RUNPOD_ENDPOINT_ID": "",
            "EMBEDDINGS_PROVIDER": "none",
        }
    )
    sys.path.insert(0, str(ROOT / "src/api"))
    from fastapi.testclient import TestClient

    from app.contracts.common import RecommendationMeta
    from app.core import accounts, refdata
    from app.core.security import session
    from app.features.pathway import data as pathway_data
    from app.main import app

    profiles_path = ROOT / "docs/demo-cvs/profiles.json"
    profiles = json.loads(profiles_path.read_text("utf-8"))
    skills = {r["id"] for r in refdata.rows("taxonomy", "skills")}
    roles = {r["id"] for r in refdata.rows("taxonomy", "roles")}
    courses = pathway_data.course_index()
    records: list[dict[str, object]] = []
    for repeat in range(1, args.repeats + 1):
        for profile in profiles:
            case = profile["user_id"].removeprefix("demo-")
            file = next((ROOT / "docs/demo-cvs").glob(f"cv_{case.replace('-', '_')}*.pdf"))
            user_id = f"measurement-{case}-{repeat}"
            accounts.create(accounts.Account(user_id, "Synthetic measurement", None, "learner"), "")
            headers = {"X-Demo-User": session.issue(user_id), "X-Workspace": "personal"}
            record: dict[str, object] = {"case": case, "repeat": repeat, "steps": []}
            records.append(record)
            started = perf_counter()
            client = TestClient(app, headers=headers)

            def request(
                step: str,
                method: str,
                url: str,
                _client: TestClient = client,
                _record: dict = record,
                **kwargs: object,
            ) -> dict:
                before = perf_counter()
                response = _client.request(method, url, **kwargs)
                _record["steps"].append(
                    {
                        "step": step,
                        "elapsed_seconds": perf_counter() - before,
                        "http_status": response.status_code,
                    }
                )
                if response.status_code != 200:
                    raise ValueError(f"{step}: HTTP {response.status_code}")
                return response.json()

            try:
                extracted = request(
                    "cv_upload",
                    "POST",
                    "/api/v1/profile/cv?include_suggestions=false",
                    files={"file": (file.name, file.read_bytes(), "application/pdf")},
                )
                assert extracted["skills"] and not extracted["truncated"]
                questionnaire = {
                    k: profile[k]
                    for k in (
                        "segment",
                        "interests",
                        "hours_per_week",
                        "budget_myr",
                        "hrd_eligible",
                        "learning_style",
                    )
                }
                request(
                    "questionnaire", "POST", "/api/v1/profile/questionnaire", json=questionnaire
                )
                # The reviewed demo fixtures deliberately omit documented parser false positives.
                assert {s["skill_id"] for s in profile["skills"]} <= {
                    s["skill_id"] for s in extracted["skills"]
                }
                request(
                    "fixture_skill_confirmation",
                    "PUT",
                    "/api/v1/profile/skills/confirm",
                    json={"skills": profile["skills"]},
                )
                radar = request("radar", "GET", "/api/v1/trends/radar?scenario=moderate")
                matches = request("matches", "GET", "/api/v1/matches?scenario=moderate")
                target = matches["matches"][0]["role_id"]
                assert target in roles
                saved = request(
                    "save_pathway",
                    "POST",
                    "/api/v1/pathway/plans",
                    json={"role_id": target, "scenario": "moderate"},
                )
                plan = saved["pathway"]
                assert plan["role_id"] == target
                for output in (extracted, radar, matches, plan):
                    RecommendationMeta.model_validate(output["meta"])
                for step in plan["steps"]:
                    assert step["skill_id"] in skills
                    assert all(c["id"] in courses and c["source"] for c in step["courses"])
                    assert step["week_start"] <= step["week_end"]
                assert all(g["skill_id"] in skills for g in plan["unmet"])
                record.update(
                    status="completed",
                    target_role_id=target,
                    snapshot_date=plan["meta"]["snapshot_date"],
                    served_from=plan["meta"].get("served_from"),
                    source_names=[s["name"] for s in plan["meta"]["sources"]],
                    unmet_skills=len(plan["unmet"]),
                    warnings=plan["warnings"],
                    structural_checks_passed=True,
                    human_validity_review=False,
                )
            except (AssertionError, ValueError) as exc:
                record.update(
                    status="failed",
                    error=str(exc) or "Structural assertion failed",
                    structural_checks_passed=False,
                    human_validity_review=False,
                )
            finally:
                record["elapsed_seconds"] = perf_counter() - started
                client.close()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "base_revision": revision,
        "working_tree_changes": True,
        "python": platform.python_version(),
        "measurement_kind": "automated_in_process_api_fixture_journey",
        "human_testers": 0,
        "human_trials": 0,
        "manual_baseline": None,
        "persona_count": len(profiles),
        "attempts": len(records),
        "profiles_sha256": hashlib.sha256(profiles_path.read_bytes()).hexdigest(),
        "cv_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "docs/demo-cvs").glob("*.pdf"))
        },
        "taxonomy_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src/data/seed/taxonomy").glob("*.csv"))
        },
        "limitations": "Local TestClient, CSV/in-memory storage and historical fixture fallback. "
        "No browser, network transit, human review, paid model or manual baseline. "
        "First run includes cold caches; later runs share process caches. "
        "Structural checks are not independent human plan-validity review.",
        "records": records,
    }
    output = ROOT / "docs/kpi-automated-journeys.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", "utf-8")
    rows = []
    for profile in profiles:
        case = profile["user_id"].removeprefix("demo-")
        group = [r for r in records if r["case"] == case]
        times = [r["elapsed_seconds"] for r in group if r["status"] == "completed"]
        median = f"{statistics.median(times):.3f}" if times else "unavailable"
        rows.append(f"| {case} | {len(times)}/{len(group)} | {median} |")
    report = "\n".join(
        [
            "# Automated synthetic journey timings",
            "",
            f"Measured {result['measured_at_utc']}; base `{revision}` with task changes.",
            f"Sample: {len(profiles)} personas, {len(records)} API journeys; 0 human trials.",
            "",
            "CV -> questionnaire -> fixture confirmation -> radar -> matches -> saved pathway.",
            "Target selection uses the first ranked stored role ID; this is an automation choice.",
            "",
            "| Persona | Completed / attempted | Median journey seconds |",
            "|---|---:|---:|",
            *rows,
            "",
            result["limitations"],
            "",
            "Step times, statuses and input hashes: [JSON](kpi-automated-journeys.json).",
            "Human trials remain in [the unfilled template](kpi-trials-template.json).",
            "The [calculator](kpi-human-summary.json) reports no baseline or achieved reduction.",
            "No speed-up or human plan-validity KPI can be inferred from these measurements.",
            "",
            "The [initial raw-ID run](kpi-automated-initial-raw-id-attempts.json) is retained:",
            "10/15 completed; five uploads received HTTP 429 because raw fixture IDs shared",
            "an anonymous rate bucket. The current run uses real signed fixture sessions,",
            "with the production limiter enabled. These are separate runs, not pooled results.",
            "",
        ]
    )
    (ROOT / "docs/kpi-automated-journeys.md").write_text(report, "utf-8")
    completed = sum(r["status"] == "completed" for r in records)
    print(f"Recorded {len(records)} isolated journeys; {completed} completed")


if __name__ == "__main__":
    main()
