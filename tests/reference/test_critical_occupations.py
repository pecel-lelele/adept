"""Offline checks of the manually curated MyCOL reference, never a scoring input."""

import csv
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "docs/reference"


def test_mycol_csv_schema_and_complete_table() -> None:
    with (REFERENCE / "critical-occupations.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "row_no",
            "masco4d",
            "occupation_label",
            "edition",
            "source_id",
            "source_page",
            "pdf_page",
            "retrieved_at",
        ]
        rows = list(reader)
    assert len(rows) == 66
    assert [int(row["row_no"]) for row in rows] == list(range(1, 67))
    assert len({row["masco4d"] for row in rows}) == 66
    for row in rows:
        assert re.fullmatch(r"\d{4}", row["masco4d"])
        assert row["occupation_label"].strip()
        assert row["edition"] == "2024/2025"
        assert row["source_id"] == "talentcorp-mycol-2024-2025-table7"
        assert date.fromisoformat(row["retrieved_at"])
        number = int(row["row_no"])
        assert int(row["source_page"]) == (85 if number <= 17 else 86 if number <= 48 else 87)
        assert int(row["pdf_page"]) == (44 if number <= 48 else 45)
    labels = {row["masco4d"]: row["occupation_label"] for row in rows}
    assert labels["2512"] == "Software Developers"
    assert labels["3115"] == "Mechanical Engineering Technicians"
    assert labels["8343"] == "Crane, Hoist and Related Plant Operators"


def test_mycol_provenance_matches_saved_reference() -> None:
    provenance = json.loads((REFERENCE / "critical-occupations.provenance.json").read_text("utf-8"))
    assert provenance["schema_version"] == 1
    assert provenance["source_id"] == "talentcorp-mycol-2024-2025-table7"
    assert provenance["publisher"] == "TalentCorp"
    assert provenance["source_url"].startswith("https://www.talentcorp.com.my/")
    assert provenance["source_url"].endswith(".pdf")
    assert datetime.fromisoformat(provenance["retrieved_at_utc"]).utcoffset() is not None
    assert re.fullmatch(r"[0-9a-f]{64}", provenance["source_pdf_sha256"])
    assert provenance["publication_date"] is None
    assert provenance["integration_status"] == "reference_only_not_connected"
    assert (
        provenance["csv_sha256"]
        == hashlib.sha256((REFERENCE / "critical-occupations.csv").read_bytes()).hexdigest()
    )
