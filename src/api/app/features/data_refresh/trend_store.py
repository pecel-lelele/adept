"""Accumulated per-paper trend evidence (M1-018): the cache behind on-demand refresh.

Papers are matched to skills once and stored with their submission day. A refresh only
fetches and matches days not stored yet; every snapshot window is a SQL count over stored rows.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

import psycopg

from app.core import refdata
from app.core.db import connection
from app.features.data_refresh import service


def fetched_days() -> dict[date, date]:
    """Stored days and when each was fetched. A missing table means no migration yet."""
    try:
        with connection() as conn:
            rows = conn.execute("SELECT day, fetched_on FROM trend_fetched_days").fetchall()
    except psycopg.errors.UndefinedTable as exc:
        raise service.RefreshFailed(
            "refresh_not_configured", "Apply the trend paper-store migration before inference."
        ) from exc
    return {row["day"]: row["fetched_on"] for row in rows}


def last_fetched(start: date, end: date) -> date | None:
    """Newest fetch date among stored days in [start, end]."""
    with connection() as conn:
        row = conn.execute(
            "SELECT max(fetched_on) AS d FROM trend_fetched_days WHERE day BETWEEN %s AND %s",
            (start, end),
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
            "SELECT threshold FROM trend_fallback_calibration WHERE model = %s", (model,)
        ).fetchone()
    return float(row["threshold"]) if row else None


def save_calibration(conn: Any, model: str, threshold: float, rate: float, day: date) -> None:
    conn.execute(
        "INSERT INTO trend_fallback_calibration(model, threshold, reference_rate, calibrated_on) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (model) DO NOTHING",
        (model, threshold, rate, day),
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

    A refetched day (see `automatic_trends.SETTLE_DAYS`) replaces its earlier papers, so the
    per-day sample stays the newest PER_DAY papers of a fully announced day.
    """
    for day, papers in days.items():
        conn.execute("DELETE FROM trend_paper_mentions WHERE published_on = %s", (day,))
        conn.execute(
            "INSERT INTO trend_fetched_days(day, papers, fetched_on) VALUES (%s, %s, %s) "
            "ON CONFLICT (day) DO UPDATE SET papers = EXCLUDED.papers, "
            "fetched_on = EXCLUDED.fetched_on",
            (day, len(papers), fetched_on),
        )
        for paper in papers:
            conn.execute(
                "INSERT INTO trend_paper_mentions(arxiv_id, published_on, method, model, skills) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (arxiv_id) DO NOTHING",
                (paper["arxiv_id"], day, method, model, mentions.get(paper["arxiv_id"], [])),
            )


def window(
    start: date, end: date, skill_ids: Iterable[str]
) -> tuple[dict[str, int], int, list[dict[str, str]], list[str]]:
    """Counts per skill, papers, sampled IDs and models for stored days in [start, end]."""
    with connection() as conn:
        total = conn.execute(
            "SELECT COALESCE(sum(papers), 0) AS n FROM trend_fetched_days "
            "WHERE day BETWEEN %s AND %s",
            (start, end),
        ).fetchone()["n"]
        counted = conn.execute(
            "SELECT s AS skill_id, count(*) AS n FROM trend_paper_mentions, unnest(skills) s "
            "WHERE published_on BETWEEN %s AND %s GROUP BY s",
            (start, end),
        ).fetchall()
        papers = conn.execute(
            "SELECT arxiv_id, published_on, model FROM trend_paper_mentions "
            "WHERE published_on BETWEEN %s AND %s ORDER BY published_on, arxiv_id",
            (start, end),
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
                "FROM trend_fetched_days"
            ).fetchone()
    except psycopg.errors.UndefinedTable:
        return None
    return (row["first"], row["last"], row["fetched"]) if row and row["first"] else None


def daily(
    start: date, end: date, skill_ids: Iterable[str]
) -> tuple[dict[date, int], dict[tuple[date, str], int]]:
    """Paper totals and mentions from one SQL/MVCC snapshot, even during day replacement."""
    wanted = list(skill_ids)
    with connection() as conn:
        rows = conn.execute(
            "WITH days AS ("
            "SELECT day, papers FROM trend_fetched_days WHERE day BETWEEN %s AND %s"
            "), mentions AS ("
            "SELECT published_on AS day, s AS skill_id, count(*) AS n "
            "FROM trend_paper_mentions, unnest(skills) s "
            "WHERE published_on BETWEEN %s AND %s AND s = ANY(%s) GROUP BY 1, 2"
            ") SELECT days.day, days.papers, mentions.skill_id, mentions.n "
            "FROM days LEFT JOIN mentions USING (day)",
            (start, end, start, end, wanted),
        ).fetchall()
    return (
        {r["day"]: int(r["papers"]) for r in rows},
        {(r["day"], r["skill_id"]): int(r["n"]) for r in rows if r["skill_id"] is not None},
    )
