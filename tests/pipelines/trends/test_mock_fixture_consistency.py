"""tests/pipelines/trends/test_mock_fixture_consistency.py

Enforces internal consistency between committed mock fixtures and score.py formulas.
Zero hand-authoring of derived fields: velocity_fast, direction_moderate, and
direction_fast must match score.py's pure functions within floating-point tolerance.
"""

from __future__ import annotations

import json
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

        # 1. velocity_fast consistency
        expected_v_fast = scenario_fast(v_mod, exp)
        assert abs(v_fast - expected_v_fast) < 1e-6, (
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


def test_specific_reported_defects_are_fixed() -> None:
    """Explicitly verify the two examples flagged by Greptile/CI."""
    with (SEED_DIR / "mock_trends.json").open(encoding="utf-8") as fh:
        items = {i["skill_id"]: i for i in json.load(fh)["items"]}

    # trade-confirmation: velocity_moderate=-0.09 must be "declining", not "stable"
    tc = items["trade-confirmation"]
    assert tc["velocity_moderate"] == -0.09
    assert tc["direction_moderate"] == "declining"

    # audit-internal: velocity_moderate=0.05, exposure=0.25 -> 0.10625, not 0.13
    ai = items["audit-internal"]
    assert ai["velocity_moderate"] == 0.05
    assert ai["automation_exposure"] == 0.25
    assert abs(ai["velocity_fast"] - 0.10625) < 1e-6
    assert ai["direction_fast"] == "rising"
