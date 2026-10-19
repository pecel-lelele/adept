import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from pipelines.pathway import run

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_sample.json"
SEED = Path(__file__).resolve().parents[3] / "src" / "data" / "seed"


def _payload() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_curated_items_are_read_from_the_catalog() -> None:
    rows = run.from_catalog(_payload(), date(2026, 10, 20))
    assert len(rows) == len(run.CURATED)
    for r in rows:
        assert r.provider == "Microsoft Learn" and r.cost_myr == 0 and not r.hrd_claimable
        assert r.url.startswith("https://learn.microsoft.com/") and "?" not in r.url
        assert r.hours > 0 and r.verified_at == date(2026, 10, 20)


def test_a_retired_uid_fails_loudly() -> None:
    payload = _payload()
    payload["modules"] = payload["modules"][1:]
    with pytest.raises(ValueError, match="retired"):
        run.from_catalog(payload, date(2026, 10, 20))


def test_unknown_skill_ids_are_rejected() -> None:
    bad = run.CourseRow(**{**run.MANUAL[0].__dict__, "skill_ids": ("made-up-skill",)})
    with pytest.raises(ValueError, match="unknown skill"):
        run.validate([bad], run.known_skills())


def test_manual_rows_state_their_hrd_evidence() -> None:
    for row in run.MANUAL:
        assert row.hrd_claimable and row.hrd_note and row.source_url.startswith("https://")


def test_main_writes_the_seed(tmp_path: Path) -> None:
    out = tmp_path / "courses.csv"
    run.main(["--from-file", str(FIXTURE), "--out", str(out), "--retrieved", "2026-10-20"])
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(run.CURATED) + len(run.MANUAL)
    assert rows[-1]["skill_ids"] == "{sql,python,data-visualisation}"


def test_committed_catalogue_matches_the_pipeline() -> None:
    with (SEED / "courses" / "courses.csv").open(encoding="utf-8") as fh:
        ids = [row["id"] for row in csv.DictReader(fh)]
    assert ids == [c.id for c in run.CURATED] + [m.id for m in run.MANUAL]
