import csv
import json
import urllib.error
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.features.pathway import catalogue_sources as src
from pipelines.pathway import run

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_sample.json"
SEED = Path(__file__).resolve().parents[3] / "src" / "data" / "seed"


def _payload() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_curated_items_are_read_from_the_catalog() -> None:
    rows = src.from_mslearn(_payload(), date(2026, 10, 20))
    assert len(rows) == len(src.CURATED)
    for r in rows:
        assert r.provider == "Microsoft Learn" and r.cost_myr == 0 and not r.hrd_claimable
        assert r.url.startswith("https://learn.microsoft.com/") and "?" not in r.url
        assert r.hours > 0 and r.verified_at == date(2026, 10, 20) and r.provider_ref


def test_a_retired_uid_fails_loudly_offline_but_is_skipped_in_sync() -> None:
    payload = _payload()
    payload["modules"] = payload["modules"][1:]
    with pytest.raises(ValueError, match="retired"):
        src.from_mslearn(payload, date(2026, 10, 20))
    rows = src.from_mslearn(payload, date(2026, 10, 20), allow_missing=True)
    assert len(rows) == len(src.CURATED) - 1
    assert len(src.missing_curated(payload)) == 1


def test_unknown_skill_ids_are_rejected() -> None:
    bad = replace(src.MANUAL[0], skill_ids=("made-up-skill",))
    with pytest.raises(ValueError, match="unknown skill"):
        src.validate([bad], run.known_skills())


def test_hrd_claims_must_quote_the_provider() -> None:
    bad = replace(src.MANUAL[0], hrd_note="")
    with pytest.raises(ValueError, match="HRD Corp claim"):
        src.validate([bad], run.known_skills())
    for row in src.MANUAL:
        assert row.hrd_claimable and row.cost_myr > 0 and row.source_url.startswith("https://")


def test_coursera_rows_are_free_to_enrol_and_state_their_hours() -> None:
    for row in src.COURSERA:
        assert row.cost_myr == 0 and not row.hrd_claimable
        assert row.url == f"https://www.coursera.org/learn/{row.provider_ref}"
        assert "module hours" in row.duration_note and "Enroll for free" in row.hrd_note


def test_coursera_status_distinguishes_gone_from_unknown() -> None:
    def gone(url: str, timeout: int) -> Any:
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    def down(url: str, timeout: int) -> Any:
        raise urllib.error.URLError("offline")

    assert src.coursera_status("x", lambda u, t: {"elements": [{"id": "1"}]}) is True
    assert src.coursera_status("x", gone) is False
    assert src.coursera_status("x", down) is None


def test_main_writes_the_seed(tmp_path: Path) -> None:
    out = tmp_path / "courses.csv"
    run.main(["--from-file", str(FIXTURE), "--out", str(out), "--retrieved", "2026-10-20"])
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(src.CURATED) + len(src.COURSERA) + len(src.MANUAL)
    assert {"provider_ref", "hrd_note", "duration_note"} <= set(rows[0])


def test_committed_catalogue_matches_the_sources() -> None:
    with (SEED / "courses" / "courses.csv").open(encoding="utf-8") as fh:
        ids = [row["id"] for row in csv.DictReader(fh)]
    expected = [c.id for c in src.CURATED] + [c.id for c in src.COURSERA]
    assert ids == expected + [m.id for m in src.MANUAL]


def test_catalogue_covers_more_skills_than_the_skeleton() -> None:
    with (SEED / "courses" / "courses.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    skills = {s for r in rows for s in r["skill_ids"].strip("{}").split(",")}
    assert {"excel", "logistics-planning", "risk-compliance", "prompt-engineering"} <= skills
    assert sum(r["hrd_claimable"] == "true" for r in rows) >= 5
