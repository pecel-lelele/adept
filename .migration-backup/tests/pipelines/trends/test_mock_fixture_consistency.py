"""tests/pipelines/trends/test_mock_fixture_consistency.py

Enforces:
1. Mathematical formula consistency between committed mock fixtures and score.py pure functions.
2. Verifiable faithful export: fixtures in src/data/seed/ match the actual rows in PostgreSQL
   trend_snapshots table for both snapshot dates (when DB is available).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from pipelines.trends.score import direction, scenario_fast

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"

FIXTURE_FILES = [
    SEED_DIR / "mock_trends.json",
    SEED_DIR / "mock_trends_2026-10-13.json",
    SEED_DIR / "mock_trends_2026-10-20.json",
]


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=lambda p: p.name)
def test_mock_fixture_derived_fields_match_scoring_formula(fixture_path: Path) -> None:
    assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"

    with fixture_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    items = data.get("items", [])
    assert items, f"Fixture {fixture_path.name} has no items"

    for item in items:
        sid = item["skill_id"]
        v_mod = float(item["velocity_moderate"])
        exp = float(item["automation_exposure"])
        v_fast = float(item["velocity_fast"])
        dir_mod = item["direction_moderate"]
        dir_fast = item["direction_fast"]

        # 1. velocity_fast consistency (1e-5 accommodates 6-decimal rounding in pipeline)
        expected_v_fast = scenario_fast(v_mod, exp)
        assert abs(v_fast - expected_v_fast) < 1e-5, (
            f"[{fixture_path.name}] {sid}: velocity_fast {v_fast} != "
            f"expected {expected_v_fast} from scenario_fast({v_mod}, {exp})"
        )

        # 2. direction_moderate consistency
        expected_dir_mod = direction(v_mod)
        assert dir_mod == expected_dir_mod, (
            f"[{fixture_path.name}] {sid}: direction_moderate '{dir_mod}' != "
            f"expected '{expected_dir_mod}' from direction({v_mod})"
        )

        # 3. direction_fast consistency
        expected_dir_fast = direction(v_fast)
        assert dir_fast == expected_dir_fast, (
            f"[{fixture_path.name}] {sid}: direction_fast '{dir_fast}' != "
            f"expected '{expected_dir_fast}' from direction({v_fast})"
        )


@pytest.mark.parametrize(
    "snap_date_str",
    ["2026-10-13", "2026-10-20"],
)
def test_mock_fixtures_faithfully_match_database_export(snap_date_str: str) -> None:
    """Assert fixture is a provably faithful export of DB rows for that snapshot date."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings
    from app.core.db import database_status

    if database_status() != "ok" or not get_settings().database_url:
        pytest.skip("PostgreSQL unavailable; skipping DB export comparison.")

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT skill_id, research_velocity, labor_decay, labor_decay_source_note,
                       automation_exposure, velocity_moderate, velocity_fast,
                       direction_moderate, direction_fast
                FROM trend_snapshots
                WHERE snapshot_date = %s
                ORDER BY skill_id
                """,
                (date.fromisoformat(snap_date_str),),
            )
            db_rows = {r["skill_id"]: r for r in cur.fetchall()}

    if not db_rows:
        pytest.skip(f"No DB rows in trend_snapshots for {snap_date_str}")

    fixture_path = SEED_DIR / f"mock_trends_{snap_date_str}.json"
    with fixture_path.open(encoding="utf-8") as fh:
        fixture_items = {i["skill_id"]: i for i in json.load(fh)["items"]}

    assert len(fixture_items) == len(db_rows), (
        f"Fixture item count ({len(fixture_items)}) != DB row count ({len(db_rows)})"
    )

    for sid, db_row in db_rows.items():
        assert sid in fixture_items, f"Missing skill {sid} in {fixture_path.name}"
        f_item = fixture_items[sid]

        assert abs(f_item["research_velocity"] - float(db_row["research_velocity"])) < 1e-5
        assert abs(f_item["labor_decay"] - float(db_row["labor_decay"])) < 1e-5
        assert f_item["labor_decay_source_note"] == db_row["labor_decay_source_note"]
        assert abs(f_item["automation_exposure"] - float(db_row["automation_exposure"])) < 1e-5
        assert abs(f_item["velocity_moderate"] - float(db_row["velocity_moderate"])) < 1e-5
        assert abs(f_item["velocity_fast"] - float(db_row["velocity_fast"])) < 1e-5
        assert f_item["direction_moderate"] == db_row["direction_moderate"]
        assert f_item["direction_fast"] == db_row["direction_fast"]
