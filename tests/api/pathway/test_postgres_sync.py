"""Live sync writes the catalogue and SDG data into PostgreSQL (fixtures, no network)."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
import pytest

from app.core import refdata
from app.core.config import get_settings
from app.features.pathway import data
from app.features.pathway.sync import sync_catalogue
from app.features.sdg import repository as sdg_repository
from app.features.sdg.sync import sync_sdg

pytestmark = pytest.mark.usefixtures("pg_backend")
FIXTURES = Path(__file__).resolve().parents[2] / "pipelines"
CATALOG = FIXTURES / "pathway" / "fixtures" / "catalog_sample.json"
GOALS = FIXTURES / "sdg" / "fixtures" / "goal_list_sample.json"


def _catalog() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(CATALOG.read_text(encoding="utf-8"))
    return payload


def _syncs(source_like: str) -> list[tuple[str, int]]:
    with psycopg.connect(get_settings().database_url) as conn:
        rows = conn.execute(
            "SELECT status, records FROM data_syncs WHERE source LIKE %s ORDER BY id DESC",
            (source_like,),
        ).fetchall()
    return [(str(s), int(r)) for s, r in rows]


def test_catalogue_sync_refreshes_and_retires() -> None:
    payload = _catalog()
    payload["modules"] = [
        m for m in payload["modules"] if m["uid"] != "learn-bizapps.pad-excel-automation"
    ]
    report = sync_catalogue(
        payload, date(2026, 10, 21), coursera_check=lambda slug: slug != "supply-chain-logistics"
    )
    try:
        assert report.status == "ok" and report.retired == 2, report.detail
        ids = {c.id for c in data.catalogue()}
        assert "mslearn-pad-excel" not in ids and "coursera-supply-chain-logistics" not in ids
        assert "unimas-excel-booster" in ids
        assert _syncs("Course catalogue%")[0][0] == "ok"
    finally:
        # Restore: a full sync un-retires everything.
        again = sync_catalogue(_catalog(), date(2026, 10, 20), coursera_check=lambda slug: True)
        assert again.status == "ok" and again.retired == 0
        refdata.invalidate()
        assert "mslearn-pad-excel" in {c.id for c in data.catalogue()}


def test_unknown_coursera_status_keeps_the_course() -> None:
    report = sync_catalogue(_catalog(), date(2026, 10, 20), coursera_check=lambda slug: None)
    assert report.status == "ok" and report.retired == 0
    assert "Coursera unreachable" in report.detail


def test_failed_source_is_logged_and_changes_nothing() -> None:
    before = {c.id for c in data.catalogue()}
    report = sync_catalogue({"modules": "not-a-list"}, date(2026, 10, 20), lambda s: True)
    assert report.status == "failed" and report.records == 0
    refdata.invalidate()
    assert {c.id for c in data.catalogue()} == before
    assert _syncs("Course catalogue%")[0][0] == "failed"


def test_sdg_sync_stamps_targets_and_upserts_evidence() -> None:
    payload = json.loads(GOALS.read_text(encoding="utf-8"))
    report = sync_sdg(payload, date(2026, 10, 21))
    assert report.status == "ok", report.detail
    refdata.invalidate()
    links = sdg_repository.skill_links("excel")
    assert links and all(link.evidence for link in links)
    with psycopg.connect(get_settings().database_url) as conn:
        stamped = conn.execute("SELECT retrieved_at FROM sdg_targets WHERE id = '1.1'").fetchone()
        dropped = conn.execute(
            "SELECT count(*) FROM skill_sdg_map WHERE skill_id = 'python' AND sdg_target_id = '9.5'"
        ).fetchone()
    assert stamped is not None and stamped[0] == date(2026, 10, 21)
    assert dropped is not None and dropped[0] == 0, "links removed from the files are removed"
