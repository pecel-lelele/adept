"""Dated inputs sufficient to rebuild a measured snapshot without network or embeddings."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any, Literal

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.contracts.common import TrendSource
from app.core import refdata
from app.core.db import connection
from app.features.data_refresh import service
from pipelines.trends import run as pipeline
from pipelines.trends import score
from pipelines.trends.encoder import MODEL_ID, MODEL_REVISION

ARXIV_API = "https://export.arxiv.org/api/query"


class MeasuredInputs(BaseModel):
    # M1-014: RunPod MiniLM; M1-017: calibrated Gemini fallback (trend_fallback).
    method: Literal["M1-014", "M1-017"] = "M1-014"
    model: str = MODEL_ID
    model_revision: str = MODEL_REVISION
    previous: tuple[date, date]
    current: tuple[date, date]
    fetched: date
    counts_before: dict[str, int]
    counts_after: dict[str, int]
    total_before: int = Field(gt=0)
    total_after: int = Field(gt=0)
    skill_ids: list[str]
    labor_decay: dict[str, tuple[float, str]]
    automation_exposure: dict[str, float]
    # Only public identifiers and publication dates; no authors or abstract text.
    sample: list[dict[str, str]]
    sources: list[TrendSource]
    note: str


def load(day: date | None = None, *, required_schema: bool = False) -> MeasuredInputs | None:
    where = "WHERE measured_date=%s" if day else ""
    try:
        with connection() as conn:
            row = conn.execute(
                f"SELECT payload FROM measured_trend_inputs {where} "
                "ORDER BY measured_date DESC LIMIT 1",
                (day,) if day else (),
            ).fetchone()
    except psycopg.errors.UndefinedTable as exc:
        if required_schema:
            raise service.RefreshFailed(
                "refresh_not_configured", "Apply the measured-input migration before inference."
            ) from exc
        return None  # legacy rescore remains available before activation
    return MeasuredInputs.model_validate(row["payload"]) if row else None


def load_minilm_reference(day: date) -> MeasuredInputs | None:
    """Stored MiniLM (M1-014) inputs to calibrate the Gemini fallback, never a fallback run.

    Prefers the week ending on `day`, otherwise the latest MiniLM week."""
    try:
        with connection() as conn:
            row = conn.execute(
                "SELECT payload FROM measured_trend_inputs "
                "WHERE COALESCE(payload->>'method', 'M1-014') = 'M1-014' "
                "ORDER BY (measured_date = %s) DESC, measured_date DESC LIMIT 1",
                (day,),
            ).fetchone()
    except psycopg.errors.UndefinedTable:
        return None
    return MeasuredInputs.model_validate(row["payload"]) if row else None


def rows(inputs: MeasuredInputs) -> list[dict[str, Any]]:
    known = {r["id"] for r in refdata.rows("taxonomy", "skills")}
    ids = set(inputs.skill_ids)
    if not ids <= known or set(inputs.counts_before) != ids or set(inputs.counts_after) != ids:
        raise service.RefreshFailed("validation_failed", "Stored inputs contain unknown skills.")
    if (
        inputs.previous[1] + timedelta(days=1) != inputs.current[0]
        or inputs.previous[1] - inputs.previous[0] != timedelta(days=6)
        or inputs.current[1] - inputs.current[0] != timedelta(days=6)
        or inputs.previous[0].weekday() != 0
        or inputs.fetched < inputs.current[1]
        or any(value < 0 or value > inputs.total_before for value in inputs.counts_before.values())
        or any(value < 0 or value > inputs.total_after for value in inputs.counts_after.values())
    ):
        raise service.RefreshFailed(
            "validation_failed", "Stored measured dates or counts are invalid."
        )
    result = score.score_rows(
        inputs.counts_before,
        inputs.total_before,
        inputs.counts_after,
        inputs.total_after,
        inputs.labor_decay,
        inputs.automation_exposure,
        skill_ids=set(inputs.skill_ids),
    )
    evidenced = [row for row in result if row.get("has_evidence", True)]

    def week(day: date) -> str:
        year, number, _ = day.isocalendar()
        return f"{year}-W{number:02}"

    if pipeline.validate(evidenced, known, week(inputs.previous[0]), week(inputs.current[0])):
        raise service.RefreshFailed(
            "validation_failed", "Stored measured inputs failed validation."
        )
    return evidenced


def arxiv_query(start: date, end: date) -> str:
    return f"cat:cs.AI AND submittedDate:[{start:%Y%m%d}0000 TO {end:%Y%m%d}2359]"


def provenance(inputs: MeasuredInputs) -> dict[str, object]:
    """Live (never replay) provenance for a measured week, from the stored fetch facts.

    The observation window is the measured current week; retrieval is the real fetch day,
    evidenced by the arXiv query, both windows and a hash of the sampled paper IDs.
    """
    ids = "\n".join(sorted(paper["id"] for paper in inputs.sample))
    digest = hashlib.sha256(ids.encode("utf-8")).hexdigest()
    previous, current = inputs.previous, inputs.current
    evidence = (
        f"{ARXIV_API}?search_query={arxiv_query(*current)} (vs {arxiv_query(*previous)}); "
        f"window={current[0]}..{current[1]} vs {previous[0]}..{previous[1]}; "
        f"fetched={inputs.fetched}; sample={len(inputs.sample)} ids sha256={digest}"
    )
    return {
        "is_replay": False,
        "observation_window_start": current[0],
        "observation_window_end": current[1],
        "retrieved_at": inputs.fetched,
        "retrieved_at_basis": "pipeline_fetch",
        "retrieval_evidence": evidence,
    }


def _sources(inputs: MeasuredInputs, facts: dict[str, object]) -> list[dict[str, Any]]:
    """Every source carries its retrieval basis; inputs stored before bases existed get
    the measured fetch (arXiv) or the static BLS sidecar evidence, never a newer date."""
    result = []
    for source in inputs.sources:
        item = source.model_dump(mode="json")
        if source.url == ARXIV_API and not source.retrieval_evidence:
            item.update(
                retrieved_at=inputs.fetched.isoformat(),
                retrieved_at_basis="pipeline_fetch",
                retrieval_evidence=facts["retrieval_evidence"],
            )
        elif source.retrieved_at_basis == "unknown":
            if source.url == pipeline.BLS_URL:
                bls = pipeline.bls_retrieval()
                item.update(
                    retrieved_at=bls["retrieved_at"],
                    retrieved_at_basis=bls["retrieved_at_basis"],
                    retrieval_evidence=bls["retrieval_evidence"],
                )
        result.append(item)
    return result


def publish(conn: Any, inputs: MeasuredInputs, scored: list[dict[str, Any]]) -> None:
    """Caller owns the fenced transaction; input and snapshot are committed together."""
    facts = provenance(inputs)
    conn.execute(
        "INSERT INTO measured_trend_inputs(measured_date,retrieved_at,payload) VALUES (%s,%s,%s) "
        "ON CONFLICT(measured_date) DO UPDATE SET retrieved_at=excluded.retrieved_at, "
        "payload=excluded.payload",
        (inputs.current[1], inputs.fetched, Jsonb(inputs.model_dump(mode="json"))),
    )
    pipeline.publish(
        scored,
        inputs.current[1],
        _sources(inputs, facts),
        inputs.note,
        "",
        provenance=facts,
        conn=conn,
    )
