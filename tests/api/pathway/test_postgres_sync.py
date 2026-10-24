"""Live sync writes the catalogue and SDG data into PostgreSQL (fixtures, no network)."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
import pytest

from app.core import refdata
from app.core.config import get_settings
from app.features.pathway import catalogue_sources as src
from app.features.pathway import data
from app.features.pathway.sync import sync_catalogue
from app.features.sdg import repository as sdg_repository
from app.features.sdg.sync import sync_sdg

pytestmark = pytest.mark.usefixtures("pg_backend")
FIXTURES = Path(__file__).resolve().parents[2] / "pipelines"
CATALOG = FIXTURES / "pathway" / "fixtures" / "catalog_sample.json"
GOALS = FIXTURES / "sdg" / "fixtures" / "goal_list_sample.json"


FX = (4.2, date(2026, 10, 21))


def _fx() -> tuple[float, date]:
    return FX


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
        payload,
        date(2026, 10, 21),
        coursera_check=lambda slug: slug != "supply-chain-logistics",
        fx=_fx,
    )
    try:
        assert report.status == "ok" and report.retired == 2, report.detail
        ids = {c.id for c in data.catalogue()}
        assert "mslearn-pad-excel" not in ids and "coursera-supply-chain-logistics" not in ids
        assert "unimas-excel-booster" in ids
        assert _syncs("Course catalogue%")[0][0] == "ok"
    finally:
        # Restore: a full sync un-retires everything.
        again = sync_catalogue(
            _catalog(), date(2026, 10, 20), coursera_check=lambda slug: True, fx=_fx
        )
        assert again.status == "ok" and again.retired == 0
        refdata.invalidate()
        assert "mslearn-pad-excel" in {c.id for c in data.catalogue()}


def test_unknown_coursera_status_keeps_the_course() -> None:
    report = sync_catalogue(
        _catalog(), date(2026, 10, 20), coursera_check=lambda slug: None, fx=_fx
    )
    assert report.status == "ok" and report.retired == 0
    assert "Coursera unreachable" in report.detail


def test_unknown_coursera_status_does_not_bring_a_retired_course_back() -> None:
    gone = "coursera-supply-chain-logistics"
    try:
        sync_catalogue(
            _catalog(),
            date(2026, 10, 20),
            coursera_check=lambda slug: slug != "supply-chain-logistics",
            fx=_fx,
        )
        report = sync_catalogue(
            _catalog(), date(2026, 10, 21), coursera_check=lambda slug: None, fx=_fx
        )
        assert report.status == "ok", report.detail
        refdata.invalidate()
        assert gone not in {c.id for c in data.catalogue()}, "still retired after a failed check"
    finally:
        sync_catalogue(_catalog(), date(2026, 10, 20), coursera_check=lambda slug: True, fx=_fx)
        refdata.invalidate()
    assert gone in {c.id for c in data.catalogue()}, "Coursera confirming it brings it back"


def test_failed_source_is_logged_and_changes_nothing() -> None:
    before = {c.id for c in data.catalogue()}
    report = sync_catalogue({"modules": "not-a-list"}, date(2026, 10, 20), lambda s: True, _fx)
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


def test_usd_prices_follow_the_live_exchange_rate() -> None:
    report = sync_catalogue(_catalog(), date(2026, 10, 21), coursera_check=lambda s: True, fx=_fx)
    assert report.status == "ok" and "USD at 4.2 MYR" in report.detail
    refdata.invalidate()
    plus = {c.id: c for c in data.catalogue()}["coursera-plus-annual"]
    assert plus.cost_myr == round(239 * 4.2, 2) and "4.2" in plus.price_note
    with psycopg.connect(get_settings().database_url) as conn:
        row = conn.execute(
            "SELECT selling_rate FROM fx_rates WHERE currency = 'USD' AND rate_date = %s", (FX[1],)
        ).fetchone()
    assert row is not None and float(row[0]) == 4.2
    assert src.usd_to_myr(1, 4.2) == 4.2


def test_exchange_rate_outage_keeps_the_last_saved_rate() -> None:
    later = (4.3, date(2099, 1, 1))  # newest saved rate; removed again below
    try:
        sync_catalogue(_catalog(), date(2026, 10, 21), lambda s: True, fx=lambda: later)
        report = sync_catalogue(_catalog(), date(2026, 10, 22), lambda s: True, fx=lambda: None)
        assert report.status == "ok" and "kept USD at 4.3 MYR" in report.detail
        refdata.invalidate()
        plus = {c.id: c for c in data.catalogue()}["coursera-plus-annual"]
        assert plus.cost_myr == round(239 * 4.3, 2), "not back to the seed rate"
    finally:
        with psycopg.connect(get_settings().database_url) as conn:
            conn.execute("DELETE FROM fx_rates WHERE rate_date = %s", (later[1],))
        sync_catalogue(_catalog(), date(2026, 10, 21), lambda s: True, fx=_fx)
        refdata.invalidate()
