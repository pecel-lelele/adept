"""N7: a bare Remote/Anywhere primary falls through; the seed obeys the current location rule."""

from __future__ import annotations

import csv
from datetime import date
from typing import Any

import pytest

from pipelines.jobs import run, sources
from pipelines.jobs.boards import Board


class FakeFetcher(sources.Fetcher):
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.payload


@pytest.mark.parametrize("placeholder", ["Remote", "remote", "Anywhere", " Remote - Anywhere "])
def test_placeholder_primary_counts_as_missing(placeholder: str) -> None:
    assert sources.in_malaysia(placeholder, "Kuala Lumpur, Malaysia")
    assert not sources.in_malaysia(placeholder, "Singapore")
    assert not sources.in_malaysia(placeholder)


def test_real_primary_still_wins() -> None:
    assert not sources.in_malaysia("Remote, US", "Kuala Lumpur")
    assert sources.in_malaysia("Remote - Malaysia", "Singapore")
    assert sources.in_malaysia("Miri", None)


def test_greenhouse_remote_primary_uses_the_malaysian_office() -> None:
    job = {
        "id": "synthetic-job",
        "title": "Synthetic analyst",
        "location": {"name": "Remote"},
        "offices": [{"location": "Kuala Lumpur, Malaysia"}],
    }
    found = list(
        sources.greenhouse(
            FakeFetcher({"jobs": [job]}), Board("greenhouse", "synthetic", "Synthetic")
        )
    )
    assert [p.work_mode for p in found] == ["remote"]


def _row(**kw: str) -> dict[str, str]:
    base = {field: "" for field in run.POSTING_FIELDS}
    base.update(
        id=kw.get("id", "x"),
        source="greenhouse",
        board="synthetic",
        employer="Synthetic Employer",
        title="Synthetic analyst",
        work_mode="onsite",
        skill_ids="{}",
        cert_ids="{}",
        last_seen="2026-10-23",
        active="true",
    )
    base.update(kw)
    return base


def test_refilter_drops_foreign_rows_and_keeps_counts_consistent() -> None:
    rows = [
        _row(id="a", location="Kuala Lumpur"),
        _row(id="b", location="Singapore"),
        _row(id="c", location="Remote", work_mode="remote", remote_scope="Worldwide"),
        _row(id="d", location="Hong Kong", last_seen="2026-10-01"),
    ]
    log = {
        "fetched_on": "2026-10-23",
        "boards": [{"source": "greenhouse", "board": "synthetic", "status": "ok", "kept": 3}],
    }
    kept, updated = run.refilter_locations(rows, log, date(2026, 10, 30))
    assert [r["id"] for r in kept] == ["a", "c"]
    assert updated["fetched_on"] == "2026-10-23"  # nothing was fetched again
    assert updated["boards"][0]["kept"] == 2  # only "b" came from the latest fetch
    assert updated["evaluation"]["openings"] == 2
    assert updated["location_refilter"]["dropped"] == 2
    assert updated["location_refilter"]["network"] is False


def test_committed_seed_obeys_the_current_location_rule() -> None:
    with run.POSTINGS_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and all(run.keeps_location(r) for r in rows)
    import json

    log = json.loads(run.FETCH_LOG.read_text(encoding="utf-8"))
    active = [r for r in rows if r["active"] == "true"]
    assert log["evaluation"]["openings"] == len(active)
