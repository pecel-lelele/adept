"""Trend refresh (M1-018, M1-024): new arXiv days -> match once -> store -> rolling snapshot.

Each refresh fetches only submission days not stored yet, oldest first, and matches those papers
to skills once with the series' one matcher (`trend_store.series_method`: Gemini after a passing
equivalence report, otherwise RunPod MiniLM; a failed matcher is never topped up by the other).
Catch-up works in
chunks that commit separately, so a timeout or crash keeps what was stored and the next run
resumes there. The snapshot compares the 7 days ending on the newest stored day with the 7 days
before, counted from stored rows, so the window moves daily instead of being cut at fixed weeks.

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
# First stored day of the Gemini trend history (M1-024).
START_DAY = date(2026, 1, 1)
# MiniLM keeps its original start: the January history is a reviewed one-time Gemini backfill,
# and the daily job must never turn it into an unapproved RunPod catch-up.
MINILM_START_DAY = date(2026, 10, 6)
# Newest cs.AI submissions kept per day (about the old 350-per-week sample) and days committed
# together. A 14-day chunk is about 50 s of arXiv spacing plus 7 embedding batches, so the
# 600 s trends step stores several chunks and later refreshes continue the catch-up.
PER_DAY = 50
CHUNK_DAYS = 14
# Below this much time, a new chunk could not fetch, match and commit; stop cleanly instead.
MIN_CHUNK_S = 90.0
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


def series_start() -> date:
    return (
        START_DAY if trend_store.series_method() == trend_store.GEMINI_METHOD else MINILM_START_DAY
    )


def missing_days(stored: dict[date, date], today: date) -> list[date]:
    """Oldest days to fetch: unstored announced days, and early-fetched days now settled.

    `stored` maps each stored day to the date it was fetched.
    """
    days: list[date] = []
    day = series_start()
    while day <= today - timedelta(days=ARXIV_LAG_DAYS):
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
        if not papers:
            # The API sometimes answers an empty page while throttling. A settled day is never
            # fetched again, so check twice before storing a real day as having no papers.
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


Calibrated = tuple[str, float, str, float, int]  # model, threshold, rule, rate, papers
Matched = tuple[list[list[str]], str, str, Calibrated | None]


def configured() -> bool:
    """The series' matcher can run. Nothing else substitutes for it (one method per series)."""
    if trend_store.series_method() == trend_store.MINILM_METHOD:
        return _runpod() is not None
    return trend_fallback.enabled()


def match(
    papers: list[dict[str, str]],
    skills: list[tuple[str, str]],
    budget: float,
    deadline: float,
    stop: threading.Event,
    today: date,
    *,
    patient: bool = False,
) -> Matched:
    """Skills per paper, the method, the model and any newly chosen threshold."""
    if trend_store.series_method() == trend_store.GEMINI_METHOD:
        return gemini_match(papers, skills, deadline, stop, today, patient=patient)
    runpod = _runpod()
    if runpod is None:
        raise service.RefreshFailed(
            "refresh_not_configured", "The MiniLM series needs the RunPod MiniLM worker."
        )
    ids = [sid for sid, _label in skills]
    model = RunPodEncoder(
        *runpod, timeout=max(1, min(600, budget)), deadline=deadline, cancelled=stop.is_set
    )
    labels = model.encode([label for _sid, label in skills], batch_size=64)
    vectors = dict(zip(ids, labels, strict=True))
    found = arxiv_ingest.paper_mentions(papers, ids, vectors, model)
    return found, trend_store.MINILM_METHOD, MODEL_ID, None


def reference_rate(today: date) -> tuple[float, str]:
    """MiniLM's mentions per paper and the rule that supplied it (see `trend_fallback`)."""
    rate = trend_store.minilm_rate()
    if rate is None:
        reference = measurements.load_minilm_reference(today)
        if reference is not None:
            rate = trend_fallback.mentions_per_paper(reference.counts_after, reference.total_after)
    if rate is None:
        return trend_fallback.DOCUMENTED_MINILM_RATE, trend_fallback.RULE_DOCUMENTED
    return rate, trend_fallback.RULE_MINILM


def gemini_similarities(
    papers: list[dict[str, str]],
    skills: list[tuple[str, str]],
    deadline: float,
    stop: threading.Event,
    *,
    patient: bool = False,
) -> list[dict[str, float]]:
    """Paper x skill cosine similarities from one Gemini model (M1-024)."""
    try:
        labels = trend_fallback.embed_bounded(
            [label for _sid, label in skills], deadline, stop.is_set, patient=patient
        )
        vectors = dict(zip([sid for sid, _label in skills], labels, strict=True))
        texts = [trend_fallback.paper_text(p) for p in papers]
        paper_vectors = trend_fallback.embed_bounded(texts, deadline, stop.is_set, patient=patient)
    except trend_fallback.FallbackUnavailable as exc:
        raise service.RefreshFailed(
            "fetch_failed",
            "Trend embeddings are unavailable; the last good snapshot is retained.",
            rows_fetched=len(papers),
        ) from exc
    return trend_fallback.similarities(paper_vectors, vectors)


def gemini_match(
    papers: list[dict[str, str]],
    skills: list[tuple[str, str]],
    deadline: float,
    stop: threading.Event,
    today: date,
    *,
    patient: bool = False,
) -> Matched:
    """Gemini primary matcher (M1-024): one stored threshold per model."""
    model = trend_fallback.model_label()
    threshold = trend_store.calibration(model)
    sims = gemini_similarities(papers, skills, deadline, stop, patient=patient)
    calibrated = None
    if threshold is None:
        rate, rule = reference_rate(today)
        threshold = trend_fallback.calibrated_threshold(sims, rate)
        calibrated = (model, threshold, rule, rate, len(papers))
    return trend_fallback.mentions(sims, threshold), trend_store.GEMINI_METHOD, model, calibrated


def _series_model() -> str:
    if trend_store.series_method() == trend_store.GEMINI_METHOD:
        return trend_fallback.model_label()
    return MODEL_ID


def catch_up(
    missing: list[date],
    started: float,
    budget: float,
    stop: threading.Event,
    today: date,
    *,
    patient: bool = False,
) -> tuple[int, int]:
    """Fetch, match and commit missing days chunk by chunk; returns (days stored, papers).

    A chunk that fails or times out rolls back alone, so earlier chunks stay stored. A timeout
    after some progress is a clean stop (the next run resumes); with no progress it is raised.
    """
    deadline = started + budget - 20
    skills = [(r["id"], r["label"]) for r in refdata.rows("taxonomy", "skills")]
    stored_days = papers_seen = 0
    for offset in range(0, len(missing), CHUNK_DAYS):
        if stored_days and deadline - time.monotonic() < MIN_CHUNK_S:
            break
        chunk = missing[offset : offset + CHUNK_DAYS]
        try:
            days = fetch_days(chunk, deadline, stop)
            papers = [paper for day in days.values() for paper in day]
            found, method, model, calibrated = (
                match(papers, skills, budget, deadline, stop, today, patient=patient)
                if papers
                else ([], trend_store.series_method(), _series_model(), None)
            )
            mentions = {p["arxiv_id"]: f for p, f in zip(papers, found, strict=True)}
            with repository.write_connection(started + budget) as conn:
                if calibrated:
                    trend_store.save_calibration(conn, *calibrated, today)
                trend_store.save_days(conn, days, mentions, method, model, today)
        except TimeoutError:
            if stored_days and not stop.is_set():
                break
            raise
        stored_days += len(days)
        papers_seen += len(papers)
        if len(days) < len(chunk):
            break  # the budget ended inside this chunk's fetch
    return stored_days, papers_seen


def run(started: float, budget: float, stop: threading.Event) -> service.Outcome:
    today = datetime.now(UTC).date()
    fetched_on = trend_store.fetched_days()
    missing = missing_days(fetched_on, today)
    fetched_rows = 0
    if missing:
        if not configured():
            raise service.RefreshFailed(
                "refresh_not_configured",
                "The trend series' matcher is not configured: the RunPod MiniLM worker, "
                "or Gemini embeddings once the equivalence test has passed.",
            )
        stored_days, fetched_rows = catch_up(missing, started, budget, stop, today)
        if stored_days < len(missing):
            # Publishing mid-catch-up would make an old window the newest snapshot.
            return service.Outcome(
                fetched_rows,
                0,
                0,
                f"Stored {stored_days} of {len(missing)} missing days; the next run resumes.",
            )
        fetched_on = trend_store.fetched_days()
    return publish_rolling(set(fetched_on), fetched_rows, started, budget, today)


def publish_rolling(
    stored: set[date], fetched_rows: int, started: float, budget: float, today: date
) -> service.Outcome:
    """Publish the newest complete rolling windows unless the published inputs already match."""
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
    inputs = rolling_inputs(previous, current, today)
    published = (
        measurements.load(latest[0]) if latest and window_from_note(latest[1]) == current else None
    )
    if published and published.model_dump(exclude={"note"}) == inputs.model_dump(exclude={"note"}):
        return service.Outcome(
            fetched_rows, 0, 0, f"Trends are current through {end}; no new complete day yet."
        )
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
    models = sorted(set(models_before) | set(models_after)) or [_series_model()]
    minilm = models == [MODEL_ID]
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
        f"Papers matched once and accumulated since {series_start()}, up to {PER_DAY} newest "
        f"per day. Models: {', '.join(models)}"
        + (". " if minilm else " (threshold stored per model, M1-024). ")
        + f"BLS 2023-2033 remains a static baseline retrieved {bls['retrieved_at']}."
    )
    return measurements.MeasuredInputs(
        method="M1-018",
        model=", ".join(models),
        model_revision=MODEL_REVISION if minilm else "provider-managed",
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
