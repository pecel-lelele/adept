"""Current arXiv submission weeks -> bounded MiniLM -> production scorer -> atomic snapshot.

When the RunPod MiniLM worker is missing or fails, a calibrated Gemini fallback measures the
same weeks (`trend_fallback`, M1-017), so an on-demand refresh does not depend on RunPod or
the weekly GitHub workflow.

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
from app.core.logging import get_logger
from app.features.data_refresh import measurements, repository, service, trend_fallback
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
    query = measurements.arxiv_query(start, end)
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
    stored = measurements.load(current[1], required_schema=True)
    if stored:
        scored = measurements.rows(stored)
        with repository.write_connection(started + budget) as conn:
            measurements.publish(conn, stored, scored)
        refresh.clear_trend_caches()
        return service.Outcome(
            0, len(scored), 0, "Rebuilt stored measured inputs; no inference called."
        )
    endpoint = os.environ.get("TRENDS_RUNPOD_ENDPOINT_ID", "")
    api_key = os.environ.get("TRENDS_RUNPOD_API_KEY", "")
    runpod_ready = (
        os.environ.get("TRENDS_EMBEDDING_BACKEND", "runpod") == "runpod"
        and bool(endpoint)
        and bool(api_key)
    )
    if not runpod_ready and not trend_fallback.enabled():
        raise service.RefreshFailed(
            "refresh_not_configured",
            "Automatic trend refresh needs the MiniLM worker or the Gemini embedding fallback.",
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
    counted: tuple[dict[str, int], dict[str, int]] | None = None
    method, model_id, revision = "M1-014", MODEL_ID, MODEL_REVISION
    if runpod_ready:
        reserve = FALLBACK_RESERVE_S if trend_fallback.enabled() else 0.0
        model = RunPodEncoder(
            endpoint,
            api_key,
            timeout=max(1, min(600, budget)),
            deadline=deadline - reserve,
            cancelled=stop.is_set,
        )
        try:
            vectors = dict(
                zip(
                    ids,
                    model.encode([label for _sid, label in skills], batch_size=64),
                    strict=True,
                )
            )
            counted = (
                arxiv_ingest.count_mentions(first, ids, vectors, model),
                arxiv_ingest.count_mentions(second, ids, vectors, model),
            )
        except Exception as exc:  # noqa: BLE001 - any worker failure may use the fallback
            if stop.is_set() or not trend_fallback.enabled():
                raise
            log.warning("MiniLM worker unavailable (%s); using Gemini fallback", type(exc).__name__)
    if counted is None:
        counted = gemini_counts(first, second, skills, previous, deadline, stop)
        method, model_id, revision = "M1-017", trend_fallback.model_label(), "api"
    before, after = counted
    labor = score.load_labor_decay()
    exposure = score.load_automation_exposure()
    rows = score.score_rows(
        before,
        len(first),
        after,
        len(second),
        labor,
        exposure,
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
    bls = pipeline.bls_retrieval()
    sources = [
        dict(
            name="arXiv cs.AI submission API",
            url=ARXIV_API,
            retrieved_at=today.isoformat(),
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
        f"{previous[0]}..{previous[1]}; fetched {today}. "
        f"Bounded sample up to {MAX_PAPERS} papers per week; "
        + (
            "MiniLM cosine method. "
            if method == "M1-014"
            else f"{model_id} fallback, threshold calibrated to the stored MiniLM mention rate. "
        )
        + f"BLS 2023-2033 remains a static baseline retrieved {bls['retrieved_at']}."
    )
    with repository.write_connection(started + budget) as conn:
        inputs = measurements.MeasuredInputs(
            method=method,
            model=model_id,
            model_revision=revision,
            previous=previous,
            current=current,
            fetched=today,
            counts_before=before,
            counts_after=after,
            total_before=len(first),
            total_after=len(second),
            skill_ids=ids,
            labor_decay=labor,
            automation_exposure=exposure,
            sources=sources,
            note=note,
            sample=[
                {"id": paper["arxiv_id"], "published_at": paper["published_at"]}
                for paper in first + second
            ],
        )
        measurements.publish(conn, inputs, evidenced)
    refresh.clear_trend_caches()
    return service.Outcome(
        len(first) + len(second), len(evidenced), 0, f"Published measured week ending {current[1]}."
    )


def gemini_counts(
    first: list[dict[str, str]],
    second: list[dict[str, str]],
    skills: list[tuple[str, str]],
    previous: tuple[date, date],
    deadline: float,
    stop: threading.Event,
) -> tuple[dict[str, int], dict[str, int]]:
    """Mention counts for both weeks with the calibrated Gemini fallback (M1-017)."""
    reference = measurements.load(previous[1]) or measurements.load()
    if reference is None:
        raise service.RefreshFailed(
            "refresh_not_supported",
            "No stored MiniLM measurement to calibrate the fallback; the last snapshot is kept.",
        )
    # Prefer the stored week that equals our previous window; otherwise the latest stored rate.
    rate = trend_fallback.mentions_per_paper(reference.counts_after, reference.total_after)
    try:
        labels = trend_fallback.embed_bounded(
            [label for _sid, label in skills], deadline, stop.is_set
        )
        vectors = dict(zip([sid for sid, _label in skills], labels, strict=True))
        texts = [trend_fallback.paper_text(p) for p in first + second]
        papers = trend_fallback.embed_bounded(texts, deadline, stop.is_set)
    except trend_fallback.FallbackUnavailable as exc:
        raise service.RefreshFailed(
            "fetch_failed",
            "Trend embeddings are unavailable; the last good snapshot is retained.",
            rows_fetched=len(first) + len(second),
        ) from exc
    before_sims = trend_fallback.similarities(papers[: len(first)], vectors)
    after_sims = trend_fallback.similarities(papers[len(first) :], vectors)
    threshold = trend_fallback.calibrated_threshold(before_sims, rate)
    return trend_fallback.count(before_sims, threshold), trend_fallback.count(after_sims, threshold)
