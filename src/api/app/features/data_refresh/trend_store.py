"""Accumulated per-paper trend evidence (M1-018): the cache behind on-demand refresh.

Papers are matched to skills once and stored with their submission day. A refresh only
fetches and matches days not stored yet; every snapshot window is a SQL count over stored rows.

Each day and paper is stored per method (M1-024). Every read names one method, the one selected
by `series_method()`, so a window can never mix MiniLM and Gemini days. A day the active method
has not matched is simply not stored for it (a gap), whatever other methods hold.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import date
from typing import Any

import psycopg

from app.core import refdata, seed
from app.core.db import connection
from app.features.data_refresh import service, trend_fallback

MINILM_METHOD = "M1-014"
GEMINI_METHOD = "M1-024"


EQUIVALENCE_REPORT = seed.SEED_DIR / "trends" / "paper_store" / "equivalence.json"


def equivalence_passed() -> bool:
    """A committed report says Gemini behaves like MiniLM for the configured model (M1-024)."""
    try:
        report = json.loads(EQUIVALENCE_REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return report.get("passed") is True and report.get("model") == trend_fallback.model_label()


def series_method() -> str:
    """The one method every stored-series read and write uses.

    `TRENDS_MATCHER=minilm` or `gemini` selects explicitly. By default (`auto`) the series stays
    on MiniLM until a passing equivalence report exists, so nothing switches untested.
    """
    matcher = os.environ.get("TRENDS_MATCHER", "auto").strip().lower()
    if matcher == "minilm":
        return MINILM_METHOD
    if matcher == "gemini" or equivalence_passed():
        return GEMINI_METHOD
    return MINILM_METHOD


def fetched_days() -> dict[date, date]:
    """Stored days and when each was fetched. A missing table means no migration yet."""
    try:
        with connection() as conn:
            rows = conn.execute(
                "SELECT day, fetched_on FROM trend_fetched_days WHERE method = %s",
                (series_method(),),
            ).fetchall()
    except psycopg.errors.UndefinedTable as exc:
        raise service.RefreshFailed(
            "refresh_not_configured", "Apply the trend paper-store migration before inference."
        ) from exc
    return {row["day"]: row["fetched_on"] for row in rows}


def last_fetched(start: date, end: date) -> date | None:
    """Newest fetch date among stored days in [start, end]."""
    with connection() as conn:
        row = conn.execute(
            "SELECT max(fetched_on) AS d FROM trend_fetched_days "
            "WHERE method = %s AND day BETWEEN %s AND %s",
            (series_method(), start, end),
        ).fetchone()
    return row["d"] if row else None


def minilm_rate() -> float | None:
    """Mean skills mentioned per paper across stored MiniLM-matched papers."""
    with connection() as conn:
        row = conn.execute(
            "SELECT count(*) AS n, COALESCE(sum(cardinality(skills)), 0) AS m "
            "FROM trend_paper_mentions WHERE method = 'M1-014'"
        ).fetchone()
    return row["m"] / row["n"] if row and row["n"] else None


def calibration(model: str) -> float | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT threshold FROM trend_matcher_calibration WHERE model = %s", (model,)
        ).fetchone()
    return float(row["threshold"]) if row else None


def save_calibration(
    conn: Any, model: str, threshold: float, rule: str, rate: float, papers: int, day: date
) -> None:
    """The first threshold stored for a model stays: later batches must keep volume changes."""
    conn.execute(
        "INSERT INTO trend_matcher_calibration"
        "(model, threshold, rule, reference_rate, reference_papers, calibrated_on) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (model) DO NOTHING",
        (model, threshold, rule, rate, papers, day),
    )


def save_days(
    conn: Any,
    days: dict[date, list[dict[str, str]]],
    mentions: dict[str, list[str]],
    method: str,
    model: str,
    fetched_on: date,
) -> None:
    """Store fetched days and their papers in the caller's transaction.

    A refetched day (see `automatic_trends.SETTLE_DAYS`) replaces that method's earlier papers,
    so the per-day sample stays the newest PER_DAY papers of a fully announced day. Other
    methods' rows for the same day are left alone.
    """
    for day, papers in days.items():
        # Acquire the (day, method) row lock before deleting mentions. This also serializes
        # two first-time inserts on the unique key: the later writer must wait, then delete
        # the earlier writer's papers instead of combining both samples under one total.
        conn.execute(
            "INSERT INTO trend_fetched_days(day, method, papers, fetched_on) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (day, method) DO UPDATE SET papers = EXCLUDED.papers, "
            "fetched_on = EXCLUDED.fetched_on",
            (day, method, len(papers), fetched_on),
        )
        conn.execute(
            "DELETE FROM trend_paper_mentions WHERE published_on = %s AND method = %s",
            (day, method),
        )
        for paper in papers:
            conn.execute(
                "INSERT INTO trend_paper_mentions(arxiv_id, published_on, method, model, skills) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (arxiv_id, method) DO NOTHING",
                (paper["arxiv_id"], day, method, model, mentions.get(paper["arxiv_id"], [])),
            )


def window(
    start: date, end: date, skill_ids: Iterable[str]
) -> tuple[dict[str, int], int, list[dict[str, str]], list[str]]:
    """Counts per skill, papers, sampled IDs and models for stored days in [start, end]."""
    method = series_method()
    with connection() as conn:
        total = conn.execute(
            "SELECT COALESCE(sum(papers), 0) AS n FROM trend_fetched_days "
            "WHERE method = %s AND day BETWEEN %s AND %s",
            (method, start, end),
        ).fetchone()["n"]
        counted = conn.execute(
            "SELECT s AS skill_id, count(*) AS n FROM trend_paper_mentions, unnest(skills) s "
            "WHERE method = %s AND published_on BETWEEN %s AND %s GROUP BY s",
            (method, start, end),
        ).fetchall()
        papers = conn.execute(
            "SELECT arxiv_id, published_on, model FROM trend_paper_mentions "
            "WHERE method = %s AND published_on BETWEEN %s AND %s ORDER BY published_on, arxiv_id",
            (method, start, end),
        ).fetchall()
    counts = dict.fromkeys(skill_ids, 0)
    for row in counted:
        if row["skill_id"] in counts:
            counts[row["skill_id"]] = int(row["n"])
    sample = [{"id": r["arxiv_id"], "published_at": r["published_on"].isoformat()} for r in papers]
    models = sorted({r["model"] for r in papers})
    return counts, int(total), sample, models


def stored_range() -> tuple[date, date, date] | None:
    """(first day, newest day, latest fetch date), or None when nothing is stored yet.

    Deployments without the app database (CSV demo mode) have no store; a configured but
    unreachable database still raises, so an outage is never shown as "no history"."""
    if not refdata.use_postgres():
        return None
    try:
        with connection() as conn:
            row = conn.execute(
                "SELECT min(day) AS first, max(day) AS last, max(fetched_on) AS fetched "
                "FROM trend_fetched_days WHERE method = %s",
                (series_method(),),
            ).fetchone()
    except psycopg.errors.UndefinedTable:
        return None
    return (row["first"], row["last"], row["fetched"]) if row and row["first"] else None


def daily(
    start: date, end: date, skill_ids: Iterable[str]
) -> tuple[dict[date, int], dict[tuple[date, str], int]]:
    """Paper totals and mentions from one SQL/MVCC snapshot, even during day replacement."""
    wanted = list(skill_ids)
    method = series_method()
    with connection() as conn:
        rows = conn.execute(
            "WITH days AS ("
            "SELECT day, papers FROM trend_fetched_days WHERE method = %s AND day BETWEEN %s AND %s"
            "), mentions AS ("
            "SELECT published_on AS day, s AS skill_id, count(*) AS n "
            "FROM trend_paper_mentions, unnest(skills) s "
            "WHERE method = %s AND published_on BETWEEN %s AND %s AND s = ANY(%s) GROUP BY 1, 2"
            ") SELECT days.day, days.papers, mentions.skill_id, mentions.n "
            "FROM days LEFT JOIN mentions USING (day)",
            (method, start, end, method, start, end, wanted),
        ).fetchall()
    return (
        {r["day"]: int(r["papers"]) for r in rows},
        {(r["day"], r["skill_id"]): int(r["n"]) for r in rows if r["skill_id"] is not None},
    )
