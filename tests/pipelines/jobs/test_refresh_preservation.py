"""Partial and failed board reads must not close or erase current job listings."""

from datetime import date, timedelta

import httpx
import pytest

from pipelines.jobs import run, sources
from pipelines.jobs.boards import Board

TODAY = date(2026, 10, 23)


def row(pid: str, board: str = "one", days: int = 0) -> dict:
    return {
        "id": pid,
        "source": "himalayas",
        "board": board,
        "active": "true",
        "last_seen": (TODAY - timedelta(days=days)).isoformat(),
        "expires_at": "",
    }


@pytest.mark.parametrize("status", ["partial", "error", "skipped", "blocked"])
def test_incomplete_or_skipped_boards_keep_previous_rows(status: str) -> None:
    old = [row("a"), row("other", "two"), row("stale", days=15)]
    result = {
        r["id"]: r
        for r in run.merge_postings(
            old,
            [row("new")],
            [{"source": "himalayas", "board": "one", "status": status}],
            TODAY,
        )
    }
    assert result["a"]["active"] == "true"
    assert result["other"]["active"] == "true"
    assert result["stale"]["active"] == "false"
    assert result["new"]["active"] == "true"
    assert old[2]["active"] == "true"  # input objects are not mutated


def test_complete_read_closes_only_its_missing_openings() -> None:
    result = {
        r["id"]: r
        for r in run.merge_postings(
            [row("a"), row("b", "two"), row("boundary", days=14)],
            [row("fresh")],
            [{"source": "himalayas", "board": "one", "status": "ok"}],
            TODAY,
        )
    }
    assert result["a"]["active"] == "false"
    assert result["b"]["active"] == "true"


def test_rate_limit_is_a_partial_read_not_a_success() -> None:
    class Limited:
        def get_json(self, url: str, **kwargs):
            response = httpx.Response(429, request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("rate limited", request=response.request, response=response)

    with pytest.raises(sources.IncompleteRead):
        list(sources.himalayas(Limited(), Board("himalayas", "remote", "")))


def test_fetch_keeps_yielded_rows_and_marks_partial(monkeypatch) -> None:
    board = Board("himalayas", "remote", "")

    def incomplete(*args):
        yield sources.RawPosting(
            source="himalayas",
            board="remote",
            source_id="1",
            employer="Fictional employer",
            title="Data Analyst",
            url="https://example.test/job/1",
            api_url="https://example.test/feed",
        )
        raise sources.IncompleteRead("rate limited")

    monkeypatch.setattr(run.boards, "ALL", [board])
    monkeypatch.setitem(run.CONNECTORS, "himalayas", incomplete)
    postings, log = run.fetch(None)
    assert len(postings) == 1 and log[0]["status"] == "partial" and log[0]["kept"] == 1
