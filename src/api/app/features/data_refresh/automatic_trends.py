"""On-demand trend refresh (M1-018): new arXiv days -> match once -> store -> rolling snapshot.

Each refresh fetches only submission days not stored yet (oldest first, bounded per run),
matches those papers to skills once (RunPod MiniLM, or the calibrated Gemini fallback of
M1-017 when the worker is missing or fails) and stores them (`trend_store`). The snapshot
compares the 7 days ending on the newest stored day with the 7 days before, counted from
stored rows, so the window moves daily instead of being cut at fixed weeks.

A dated sample is never moved to a newer ISO week. Inference is skipped before any network
operation when that measured week already exists. BLS remains a dated, static baseline.
"""

from __future__ import annotations

import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlencode

from app.core import refdata
from app.core.logging import get_logger
from app.features.data_refresh import (
    measurements,
    repository,
    service,
    trend_fallback,
    trend_store,
)
from app.features.trends import refresh
from app.features.trends.provenance import window_from_note
from pipelines.trends import arxiv_ingest, score
from pipelines.trends import run as pipeline
from pipelines.trends.encoder import MODEL_ID, MODEL_REVISION, RunPodEncoder

log = get_logger("app.data_refresh.trends")

ARXIV_API = measurements.ARXIV_API
MAX_PAPERS = 350
MAX_BYTES = 8_000_000
NS = {"a": "http://www.w3.org/2005/Atom"}
# Time held back from RunPod so the Gemini fallback can still finish inside the run budget.
FALLBACK_RESERVE_S = 90.0
# First stored day: one week before the first live snapshot (13 Oct 2026).
START_DAY = date(2026, 10, 6)
# Newest cs.AI submissions kept per day (about the old 350-per-week sample) and days per run,
# so one refresh stays inside its time budget; later refreshes continue the backfill.
PER_DAY = 50
MAX_DAYS_PER_RUN = 14
WINDOW_DAYS = 7
ARXIV_SPACING_S = 3.5  # arXiv API cadence
# arXiv lists a paper only after its announcement (weekend submissions wait until Monday
# evening ET), so a day is first fetched ARXIV_LAG_DAYS after it ends. A day fetched before
# SETTLE_DAYS is fetched once more after that and its papers are replaced, so late
# announcements are never lost; settled days are never fetched again.
ARXIV_LAG_DAYS = 3
SETTLE_DAYS = 5


def periods(today: date) -> tuple[tuple[date, date], tuple[date, date]]:
    end = today - timedelta(days=today.weekday() + 1)
    return (end - timedelta(days=13), end - timedelta(days=7)), (end - timedelta(days=6), end)


def week(day: date) -> str:
    year, number, _ = day.isocalendar()
    return f"{year}-W{number:02}"


def parse_window(
    xml: bytes, start: date, end: date, *, limit: int = MAX_PAPERS, allow_empty: bool = False
) -> list[dict[str, str]]:
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
    if (not papers and not allow_empty) or len(papers) > limit:
        raise ValueError("arXiv returned an empty or oversized paper sample")
    return papers


def fetch_window(
    start: date,
    end: date,
    deadline: float,
    *,
    limit: int = MAX_PAPERS,
    allow_empty: bool = False,
) -> list[dict[str, str]]:
    query = measurements.arxiv_query(start, end)
    url = (
        ARXIV_API
        + "?"
        + urlencode(
            dict(
                search_query=query,
                start=0,
                max_results=limit,
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
    return parse_window(bytes(body), start, end, limit=limit, allow_empty=allow_empty)


def paper_key(identifier: str) -> str:
    """Stable arXiv ID without the version suffix (v1, v2 ... are the same paper)."""
    return re.sub(r"v\d+$", "", identifier.rstrip("/").rsplit("/abs/", 1)[-1])


def missing_days(stored: dict[date, date], today: date) -> list[date]:
    """Oldest days to fetch: unstored announced days, and early-fetched days now settled.

    `stored` maps each stored day to the date it was fetched.
    """
    days: list[date] = []
    day = START_DAY
    while day <= today - timedelta(days=ARXIV_LAG_DAYS) and len(days) < MAX_DAYS_PER_RUN:
        fetched_on = stored.get(day)
        settled = day + timedelta(days=SETTLE_DAYS)
        if fetched_on is None or (fetched_on < settled <= today):
            days.append(day)
        day += timedelta(days=1)
    return days


def snapshot_end(stored: set[date]) -> date | None:
    """Newest day whose two 7-day windows are fully stored."""
    for end in sorted(stored, reverse=True):
        if all(end - timedelta(days=i) in stored for i in range(2 * WINDOW_DAYS)):
            return end
    return None


def fetch_days(
    days: list[date], deadline: float, stop: threading.Event
) -> dict[date, list[dict[str, str]]]:
    """Fetch as many missing days as the budget allows, oldest first."""
    fetched: dict[date, list[dict[str, str]]] = {}
    for i, day in enumerate(days):
        if i:
            if deadline - time.monotonic() < ARXIV_SPACING_S + 60:
                break  # keep time to match and store what we have
            stop.wait(ARXIV_SPACING_S)
            if stop.is_set():
                raise TimeoutError("refresh cancelled")
        papers = fetch_window(day, day, deadline, limit=PER_DAY, allow_empty=True)
        fetched[day] = [{**p, "arxiv_id": paper_key(p["arxiv_id"])} for p in papers]
    return fetched


def _runpod() -> tuple[str, str] | None:
    endpoint = os.environ.get("TRENDS_RUNPOD_ENDPOINT_ID", "")
    api_key = os.environ.get("TRENDS_RUNPOD_API_KEY", "")
    backend = os.environ.get("TRENDS_EMBEDDING_BACKEND", "runpod")
    return (endpoint, api_key) if backend == "runpod" and endpoint and api_key else None


Matched = tuple[list[list[str]], str, str, tuple[str, float, float] | None]


def match(
    papers: list[dict[str, str]],
    skills: list[tuple[str, str]],
    budget: float,
    deadline: float,
    stop: threading.Event,
    today: date,
) -> Matched:
    """Skills per paper, the method, the model and any new fallback calibration."""
    ids = [sid for sid, _label in skills]
    runpod = _runpod()
    if runpod:
        reserve = FALLBACK_RESERVE_S if trend_fallback.enabled() else 0.0
        try:
            model = RunPodEncoder(
                *runpod,
                timeout=max(1, min(600, budget)),
                deadline=deadline - reserve,
                cancelled=stop.is_set,
            )
            labels = model.encode([label for _sid, label in skills], batch_size=64)
            vectors = dict(zip(ids, labels, strict=True))
            found = arxiv_ingest.paper_mentions(papers, ids, vectors, model)
            return found, "M1-014", MODEL_ID, None
        except Exception as exc:  # noqa: BLE001 - any worker failure may use the fallback
            if stop.is_set() or not trend_fallback.enabled():
                raise
            log.warning("MiniLM worker unavailable (%s); using Gemini fallback", type(exc).__name__)
    return gemini_match(papers, skills, deadline, stop, today)


def _reference_rate(today: date) -> float:
    rate = trend_store.minilm_rate()
    if rate is None:
        reference = measurements.load_minilm_reference(today)
        if reference is not None:
            rate = trend_fallback.mentions_per_paper(reference.counts_after, reference.total_after)
    if rate is None:
        raise service.RefreshFailed(
            "refresh_not_supported",
            "No stored MiniLM evidence to calibrate the fallback; the last snapshot is kept.",
        )
    return rate


def gemini_match(
    papers: list[dict[str, str]],
    skills: list[tuple[str, str]],
    deadline: float,
    stop: threading.Event,
    today: date,
) -> Matched:
    """Calibrated Gemini fallback (M1-017): one stored threshold per model."""
    model = trend_fallback.model_label()
    threshold = trend_store.calibration(model)
    rate = _reference_rate(today) if threshold is None else None
    try:
        labels = trend_fallback.embed_bounded(
            [label for _sid, label in skills], deadline, stop.is_set
        )
        vectors = dict(zip([sid for sid, _label in skills], labels, strict=True))
        texts = [trend_fallback.paper_text(p) for p in papers]
        paper_vectors = trend_fallback.embed_bounded(texts, deadline, stop.is_set)
    except trend_fallback.FallbackUnavailable as exc:
        raise service.RefreshFailed(
            "fetch_failed",
            "Trend embeddings are unavailable; the last good snapshot is retained.",
            rows_fetched=len(papers),
        ) from exc
    sims = trend_fallback.similarities(paper_vectors, vectors)
    calibrated = None
    if threshold is None:
        assert rate is not None
        threshold = trend_fallback.calibrated_threshold(sims, rate)
        calibrated = (model, threshold, rate)
    return trend_fallback.mentions(sims, threshold), "M1-017", model, calibrated


def run(started: float, budget: float, stop: threading.Event) -> service.Outcome:
    deadline = started + budget - 20
    today = datetime.now(UTC).date()
    fetched_on = trend_store.fetched_days()
    stored = set(fetched_on)
    missing = missing_days(fetched_on, today)
    revisited: set[date] = set()
    fetched_rows = 0
    if missing:
        if _runpod() is None and not trend_fallback.enabled():
            raise service.RefreshFailed(
                "refresh_not_configured",
                "Trend refresh needs the MiniLM worker or the Gemini embedding fallback.",
            )
        days = fetch_days(missing, deadline, stop)
        papers = [paper for day in days.values() for paper in day]
        fetched_rows = len(papers)
        skills = [(r["id"], r["label"]) for r in refdata.rows("taxonomy", "skills")]
        matched: Matched = (
            match(papers, skills, budget, deadline, stop, today)
            if papers
            else ([], "M1-014", MODEL_ID, None)
        )
        found, method, model, calibrated = matched
        mentions = {p["arxiv_id"]: f for p, f in zip(papers, found, strict=True)}
        with repository.write_connection(started + budget) as conn:
            if calibrated:
                trend_store.save_calibration(conn, *calibrated, today)
            trend_store.save_days(conn, days, mentions, method, model, today)
        revisited = set(days) & stored
        stored |= set(days)
    end = snapshot_end(stored)
    if end is None:
        return service.Outcome(
            fetched_rows,
            0,
            0,
            f"Stored {len(stored)} days; a snapshot needs {2 * WINDOW_DAYS} consecutive days.",
        )
    current = (end - timedelta(days=WINDOW_DAYS - 1), end)
    previous = (current[0] - timedelta(days=WINDOW_DAYS), current[0] - timedelta(days=1))
    latest = refresh.latest_published(repository.bounded_db_url())
    unchanged = not any(previous[0] <= d <= current[1] for d in revisited)
    if latest and window_from_note(latest[1]) == current and unchanged:
        return service.Outcome(
            fetched_rows, 0, 0, f"Trends are current through {end}; no new complete day yet."
        )
    inputs = rolling_inputs(previous, current, today)
    scored = measurements.rows(inputs)
    with repository.write_connection(started + budget) as conn:
        measurements.publish(conn, inputs, scored)
    refresh.clear_trend_caches()
    return service.Outcome(
        fetched_rows, len(scored), 0, f"Published rolling trends through {current[1]}."
    )


def rolling_inputs(
    previous: tuple[date, date], current: tuple[date, date], today: date
) -> measurements.MeasuredInputs:
    """Scorer inputs for two stored 7-day windows (no network or model calls)."""
    ids = [r["id"] for r in refdata.rows("taxonomy", "skills")]
    before, total_before, sample_before, models_before = trend_store.window(*previous, ids)
    after, total_after, sample_after, models_after = trend_store.window(*current, ids)
    if total_before <= 0 or total_after <= 0:
        raise service.RefreshFailed(
            "validation_failed", "A stored window has no papers; the last snapshot is kept."
        )
    # The arXiv retrieval date is when these stored days were fetched, not the rebuild date.
    fetched = trend_store.last_fetched(previous[0], current[1])
    if fetched is None:
        raise service.RefreshFailed(
            "validation_failed", "Stored windows have no fetch date; the last snapshot is kept."
        )
    models = sorted(set(models_before) | set(models_after)) or [MODEL_ID]
    fallback = any(m != MODEL_ID for m in models)
    bls = pipeline.bls_retrieval()
    sources = [
        dict(
            name="arXiv cs.AI submission API",
            url=ARXIV_API,
            retrieved_at=fetched.isoformat(),
            retrieved_at_basis="pipeline_fetch",
        ),
        dict(
            name="BLS Occupational Projections 2023-2033 (static baseline)",
            url=pipeline.BLS_URL,
            retrieved_at=bls["retrieved_at"],
            retrieved_at_basis=bls["retrieved_at_basis"],
            retrieval_evidence=bls["retrieval_evidence"],
        ),
    ]
    note = (
        f"Observed arXiv submissions {current[0]}..{current[1]} against "
        f"{previous[0]}..{previous[1]} (rolling 7-day windows); "
        f"last fetched {fetched}, rebuilt {today}. "
        f"Papers matched once and accumulated since {START_DAY}, up to {PER_DAY} newest "
        f"per day. Models: {', '.join(models)}"
        + (" (Gemini fallback calibrated to stored MiniLM evidence). " if fallback else ". ")
        + f"BLS 2023-2033 remains a static baseline retrieved {bls['retrieved_at']}."
    )
    return measurements.MeasuredInputs(
        method="M1-018",
        model=", ".join(models),
        model_revision="mixed" if fallback else MODEL_REVISION,
        previous=previous,
        current=current,
        fetched=fetched,
        counts_before=before,
        counts_after=after,
        total_before=total_before,
        total_after=total_after,
        skill_ids=ids,
        labor_decay=score.load_labor_decay(),
        automation_exposure=score.load_automation_exposure(),
        sources=sources,
        note=note,
        sample=sample_before + sample_after,
    )
