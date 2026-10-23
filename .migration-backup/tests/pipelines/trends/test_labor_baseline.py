"""Tests for labor baseline pipeline and CSV quoting integrity (Part 1)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LABOR_DECAY_CSV = REPO_ROOT / "src" / "data" / "seed" / "labor_decay.csv"
BLS_CSV = REPO_ROOT / "src" / "data" / "seed" / "bls_projections_2023_2033.csv"


def test_csv_quoting_round_trip_with_commas() -> None:
    """Synthetic round-trip quoting test ensuring embedded commas are preserved."""
    buffer = io.StringIO()
    fieldnames = [
        "soc_code",
        "occupation_title",
        "employment_2023_thousands",
        "employment_2033_thousands",
        "change_thousands",
        "percent_change_2023_2033",
        "annualized_rate",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    sample_row = {
        "soc_code": "43-3031",
        "occupation_title": "Bookkeeping, accounting, and auditing clerks",
        "employment_2023_thousands": "1369",
        "employment_2033_thousands": "1186",
        "change_thousands": "-183",
        "percent_change_2023_2033": "-13.4",
        "annualized_rate": "-1.34",
    }
    writer.writerow(sample_row)

    buffer.seek(0)
    reader = csv.DictReader(buffer)
    rows = list(reader)

    assert len(rows) == 1
    read_row = rows[0]
    assert read_row["soc_code"] == "43-3031"
    assert read_row["occupation_title"] == "Bookkeeping, accounting, and auditing clerks"
    assert read_row["annualized_rate"] == "-1.34"
    assert float(read_row["annualized_rate"]) == -1.34


def test_all_bls_projections_parse_and_have_sane_rates() -> None:
    """Every row in bls_projections_2023_2033.csv must parse correctly with sane bounds."""
    assert BLS_CSV.exists(), f"{BLS_CSV} does not exist"
    with BLS_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) > 0
    for r in rows:
        assert r["soc_code"], "Missing soc_code"
        assert r["occupation_title"], "Missing occupation_title"
        rate = float(r["annualized_rate"])
        # No occupation grows or shrinks by 50% or more annually
        assert -50.0 < rate < 50.0, f"Abnormal rate for {r['soc_code']}: {rate}"


def test_all_labor_decay_values_within_sane_bounds() -> None:
    """Every labor_decay in labor_decay.csv must be within [-0.5, 0.5]."""
    assert LABOR_DECAY_CSV.exists(), f"{LABOR_DECAY_CSV} does not exist"
    with LABOR_DECAY_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) > 0
    for r in rows:
        val = float(r["labor_decay"])
        assert -0.5 <= val <= 0.5, f"labor_decay out of bounds for skill_id={r['skill_id']}: {val}"
        assert r["labor_decay_source_note"], (
            f"Empty labor_decay_source_note for skill_id={r['skill_id']}"
        )


def test_specific_repaired_occupations() -> None:
    """Bookkeeping and scheduling-admin must have the exact verified rates."""
    with LABOR_DECAY_CSV.open(newline="", encoding="utf-8") as fh:
        r_map = {r["skill_id"]: r for r in csv.DictReader(fh)}

    bk = r_map["bookkeeping"]
    assert float(bk["labor_decay"]) == -0.0134
    assert "Bookkeeping, accounting, and auditing clerks" in bk["labor_decay_source_note"]

    sa = r_map["scheduling-admin"]
    assert float(sa["labor_decay"]) == -0.0071
    assert "Secretaries and administrative assistants" in sa["labor_decay_source_note"]
