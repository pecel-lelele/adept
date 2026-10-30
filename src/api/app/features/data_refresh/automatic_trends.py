"""Current arXiv submission weeks -> bounded MiniLM -> production scorer -> atomic snapshot.

A dated sample is never moved to a newer ISO week. Inference is skipped before any network
operation when that measured week already exists. BLS remains a dated, static baseline.
"""

from __future__ import annotations

import os
import threading
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlencode

from app.core import refdata
from app.features.data_refresh import repository, service
from app.features.trends import refresh
from app.features.trends.provenance import window_from_note
from pipelines.trends import arxiv_ingest, score
from pipelines.trends import run as pipeline
from pipelines.trends.encoder import RunPodEncoder

ARXIV_API = "https://export.arxiv.org/api/query"
MAX_PAPERS = 350
MAX_BYTES = 8_000_000
NS = {"a": "http://www.w3.org/2005/Atom"}


def periods(today: date) -> tuple[tuple[date, date], tuple[date, date]]:
    end = today - timedelta(days=today.weekday() + 1)
    return (end - timedelta(days=13), end - timedelta(days=7)), (end - timedelta(days=6), end)


def week(day: date) -> str:
    year, number, _ = day.isocalendar()
    return f"{year}-W{number:02}"


def parse_window(xml: bytes, start: date, end: date) -> list[dict[str, str]]:
    root = ET.fromstring(xml)
    papers = []
    for entry in root.findall("a:entry", NS):
        published = entry.findtext("a:published", default="", namespaces=NS)
        observed = date.fromisoformat(published[:10])
        if not start <= observed <= end:
            raise ValueError("arXiv returned a paper outside the measured window")
        title = " ".join(entry.findtext("a:title", default="", namespaces=NS).split())
        abstract = " ".join(entry.findtext("a:summary", default="", namespaces=NS).split())
        identifier = entry.findtext("a:id", default="", namespaces=NS)
        if (
            not identifier.startswith(("https://arxiv.org/abs/", "http://arxiv.org/abs/"))
            or not title
        ):
            raise ValueError("arXiv returned an invalid paper record")
        papers.append(
            dict(title=title, abstract=abstract, arxiv_id=identifier, published_at=published)
        )
    if not papers or len(papers) > MAX_PAPERS:
        raise ValueError("arXiv returned an empty or oversized paper sample")
    return papers


def fetch_window(start: date, end: date, deadline: float) -> list[dict[str, str]]:
    query = f"cat:cs.AI AND submittedDate:[{start:%Y%m%d}0000 TO {end:%Y%m%d}2359]"
    url = (
        ARXIV_API
        + "?"
        + urlencode(
            dict(
                search_query=query,
                start=0,
                max_results=MAX_PAPERS,
                sortBy="submittedDate",
                sortOrder="descending",
            )
        )
    )
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError("refresh time budget reached")
    with service.guarded_client() as client:
        with client.stream("GET", url, timeout=min(30, left)) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise TimeoutError("refresh time budget reached")
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ValueError("arXiv response exceeds its size limit")
    return parse_window(bytes(body), start, end)


def run(started: float, budget: float, stop: threading.Event) -> service.Outcome:
    deadline = started + budget - 20
    today = datetime.now(UTC).date()
    previous, current = periods(today)
    latest = refresh.latest_published(repository.bounded_db_url())
    if latest and window_from_note(latest[1]) == current:
        return service.Outcome(
            0, 0, 0, "The newest complete measured ISO week is already stored; no inference called."
        )
    if os.environ.get("TRENDS_EMBEDDING_BACKEND", "runpod") != "runpod":
        raise service.RefreshFailed(
            "refresh_not_configured",
            "Automatic trend refresh requires the dedicated MiniLM worker.",
        )
    model = RunPodEncoder(
        os.environ.get("TRENDS_RUNPOD_ENDPOINT_ID", ""),
        os.environ.get("TRENDS_RUNPOD_API_KEY", ""),
        timeout=max(1, min(600, budget)),
        deadline=deadline,
        cancelled=stop.is_set,
    )
    first = fetch_window(*previous, deadline)
    if deadline - time.monotonic() < 3.5:
        raise TimeoutError("refresh time budget reached")
    stop.wait(3.5)  # arXiv API cadence, interruptible on shutdown
    if stop.is_set():
        raise TimeoutError("refresh cancelled")
    second = fetch_window(*current, deadline)
    skills = [(r["id"], r["label"]) for r in refdata.rows("taxonomy", "skills")]
    ids = [sid for sid, _label in skills]
    vectors = dict(
        zip(ids, model.encode([label for _sid, label in skills], batch_size=64), strict=True)
    )
    before = arxiv_ingest.count_mentions(first, ids, vectors, model)
    after = arxiv_ingest.count_mentions(second, ids, vectors, model)
    rows = score.score_rows(
        before,
        len(first),
        after,
        len(second),
        score.load_labor_decay(),
        score.load_automation_exposure(),
        skill_ids=set(ids),
    )
    evidenced = [row for row in rows if row.get("has_evidence", True)]
    errors = pipeline.validate(evidenced, set(ids), week(previous[0]), week(current[0]))
    if errors:
        raise service.RefreshFailed(
            "validation_failed",
            "Trend evidence failed validation; the last good snapshot is retained.",
            rows_fetched=len(first) + len(second),
        )
    sources = [
        dict(name="arXiv cs.AI submission API", url=ARXIV_API, retrieved_at=today.isoformat()),
        dict(
            name="BLS Occupational Projections 2023-2033 (static baseline)",
            url=pipeline.BLS_URL,
            retrieved_at=pipeline.BLS_RETRIEVED_AT,
        ),
    ]
    note = (
        f"Observed arXiv submissions {current[0]}..{current[1]} against "
        f"{previous[0]}..{previous[1]}; fetched {today}. "
        f"Bounded sample up to {MAX_PAPERS} papers per week; MiniLM cosine method. "
        "BLS 2023-2033 remains a static baseline retrieved 2026-10-20."
    )
    with repository.write_connection(started + budget) as conn:
        pipeline.publish(
            evidenced, current[1], sources, note, repository.bounded_db_url(), conn=conn
        )
    refresh.clear_trend_caches()
    return service.Outcome(
        len(first) + len(second), len(evidenced), 0, f"Published measured week ending {current[1]}."
    )
