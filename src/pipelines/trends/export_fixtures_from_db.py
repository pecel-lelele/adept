"""src/pipelines/trends/export_fixtures_from_db.py

Exports genuine scored snapshot rows from PostgreSQL trend_snapshots directly
into offline-servable JSON fixtures:
  - src/data/seed/mock_trends_2026-10-13.json
  - src/data/seed/mock_trends_2026-10-20.json
  - src/data/seed/mock_trends.json (canonical copy of latest snapshot: 2026-10-20)

These fixtures are frozen, offline-servable copies of real scored snapshots
produced from the genuine arXiv cs.AI query API date-range pulls
(2024-10-06..2024-10-12 and 2024-10-13..2024-10-19) calibrated to 2026-W42/W43.
They do not invent or hand-author any values.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
sys.path.insert(0, str(REPO_ROOT / "src"))
from app.core.config import get_settings  # noqa: E402
from app.features.trends.provenance import provenance_values  # noqa: E402
from pipelines.trends.provenance import git_commit_retrieval  # noqa: E402

SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
CANONICAL_CSV = SEED_DIR / "canonical_skills.csv"

SNAPSHOT_DATES = ["2026-10-13", "2026-10-20"]
AVAILABLE_SNAPSHOTS = ["2026-10-13", "2026-10-20"]

PROVENANCE_NOTES = {
    "2026-10-13": (
        "Frozen offline snapshot exported from PostgreSQL trend_snapshots "
        "(measured from arXiv cs.AI query API submission window 2024-10-06..2024-10-12 "
        "calibrated as 2026-W42 baseline; static copy that does not update unless "
        "export_fixtures_from_db.py is re-run against a fresh pipeline run)."
    ),
    "2026-10-20": (
        "Frozen offline snapshot exported from PostgreSQL trend_snapshots "
        "(measured from arXiv cs.AI query API submission windows 2024-10-13..2024-10-19 "
        "vs 2024-10-06..2024-10-12 calibrated to 2026-W42/W43; static copy that does not "
        "update unless export_fixtures_from_db.py is re-run against a fresh pipeline run)."
    ),
}


def load_skill_labels() -> dict[str, str]:
    """Load canonical skill labels."""
    labels: dict[str, str] = {}
    if CANONICAL_CSV.exists():
        with CANONICAL_CSV.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                labels[row["skill_id"]] = row["skill_label"]
    return labels


def export_snapshot(
    conn: psycopg.Connection,
    snapshot_date_str: str,
    labels: dict[str, str],
) -> dict:
    sd = date.fromisoformat(snapshot_date_str)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM trend_snapshots
            WHERE snapshot_date = %s
            ORDER BY skill_id
            """,
            (sd,),
        )
        rows = cur.fetchall()
        cur.execute("SELECT * FROM trend_snapshot_meta WHERE snapshot_date = %s", (sd,))
        stored_meta = cur.fetchone() or {}

    if not rows:
        raise RuntimeError(
            f"No rows found in trend_snapshots for {snapshot_date_str}. "
            "Run populate_dual_snapshot.py first."
        )

    items = []
    for r in rows:
        sid = r["skill_id"]
        label = labels.get(sid, sid.replace("-", " ").title())
        items.append(
            {
                "skill_id": sid,
                "skill_label": label,
                "research_velocity": float(r["research_velocity"]),
                "labor_decay": float(r["labor_decay"]),
                "labor_decay_source_note": r["labor_decay_source_note"],
                "automation_exposure": float(r["automation_exposure"]),
                "velocity_moderate": float(r["velocity_moderate"]),
                "velocity_fast": float(r["velocity_fast"]),
                "direction_moderate": r["direction_moderate"],
                "direction_fast": r["direction_fast"],
            }
        )

    note = stored_meta.get("provenance_note") or PROVENANCE_NOTES.get(snapshot_date_str)
    stored = stored_meta if stored_meta.get("is_replay") is not None else rows[0]
    if stored.get("retrieved_at") is None or stored.get("retrieved_at_basis") in (None, "unknown"):
        # No verified fetch timestamp survives for these legacy replay exports. Use
        # the source fixture's evidenced commit day, never its assigned slot date.
        fixture = SEED_DIR / f"mock_trends_{snapshot_date_str}.json"
        if snapshot_date_str not in PROVENANCE_NOTES or not fixture.is_file():
            raise ValueError("Cannot export unclassified trend data without observation evidence")
        # A slot label alone cannot establish an observation window. The fallback
        # is allowed only for the same committed replay data, not arbitrary rows
        # that happen to occupy a familiar date.
        frozen = json.loads(fixture.read_text(encoding="utf-8"))
        expected = {item["skill_id"]: item for item in frozen["items"]}
        if len(expected) != len(rows) or any(
            row["skill_id"] not in expected
            or any(
                not math.isclose(
                    float(row[field]),
                    float(expected[row["skill_id"]][field]),
                    rel_tol=1e-5,
                    abs_tol=1e-5,
                )
                for field in (
                    "research_velocity",
                    "labor_decay",
                    "automation_exposure",
                    "velocity_moderate",
                    "velocity_fast",
                )
            )
            for row in rows
        ):
            raise ValueError("Legacy snapshot does not match its cited replay fixture")
        stored = {
            **stored,
            **git_commit_retrieval(fixture),
            "is_replay": True,
        }
    validated = provenance_values(stored, note)
    for row in rows:
        if row.get("is_replay") is not None and provenance_values(row) != validated:
            raise ValueError("Conflicting stored trend provenance cannot be exported")
        if row.get("is_replay") is None and validated["is_replay"] is False:
            raise ValueError("Unclassified snapshot rows cannot be exported as live")
    provenance = {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in validated.items()
    }
    sources = stored_meta.get("sources") or [
        {"name": "arXiv cs.AI Query API", "url": "http://export.arxiv.org/api/query"},
        {
            "name": "BLS Occupational Projections 2023-2033",
            "url": "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm",
        },
    ]
    sources = [
        source
        if source.get("retrieved_at_basis") not in (None, "unknown")
        else {
            **source,
            **{
                key: provenance[key]
                for key in ("retrieved_at", "retrieved_at_basis", "retrieval_evidence")
            },
        }
        for source in sources
    ]
    return {
        "meta": {
            "sources": sources,
            "snapshot_date": snapshot_date_str,
            "scenario": "moderate",
            "is_estimate": True,
            "weights": {"research_velocity": 0.6, "labor_decay": 0.4},
            "labor_decay_is_static": True,
            "available_snapshots": AVAILABLE_SNAPSHOTS,
            "data_provenance_note": note,
            **provenance,
        },
        "items": items,
    }


def main() -> None:
    db_url = get_settings().database_url
    labels = load_skill_labels()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        for snap_date in SNAPSHOT_DATES:
            data = export_snapshot(conn, snap_date, labels)
            target = SEED_DIR / f"mock_trends_{snap_date}.json"
            with target.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
            print(f"Exported {len(data['items'])} rows -> {target}")

            if snap_date == "2026-10-20":
                default_target = SEED_DIR / "mock_trends.json"
                with default_target.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
                print(f"Exported {len(data['items'])} rows -> {default_target}")

    print("DB fixture export complete.")


if __name__ == "__main__":
    main()
