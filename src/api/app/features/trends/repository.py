"""Data access layer for trend snapshots.

Strategy:
  1. Try Postgres (trend_snapshots table, written by score.py).
  2. Fall back to mock fixture (mock_trends.json) if DB is unavailable or
     has no data yet — so the endpoint is always callable in demo mode.

No network calls are made here; arXiv and BLS data are pre-fetched by the
pipeline scripts (Part 5 and Part 3 respectively).
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import ScenarioId
from app.contracts.trends import EntityType, TrendSignal, TrendSnapshotResponse
from app.features.trends import mocks

# ---------------------------------------------------------------------------
# Live DB reader (used when Postgres has scored snapshots)
# ---------------------------------------------------------------------------


def _db_available() -> bool:
    try:
        import psycopg  # noqa: F401 – optional runtime dep

        from app.core.config import get_settings
        from app.core.db import database_status

        return database_status() == "ok" and get_settings().database_url != ""
    except Exception:
        return False


def _list_snapshot_dates_db() -> list[date]:
    """Return all snapshot dates present in the trend_snapshots table."""
    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row

    from app.core.config import get_settings

    try:
        with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date"
                )
                return [row["snapshot_date"] for row in cur.fetchall()]
    except Exception:
        return []


def _load_snapshot_db(snapshot_date: date, scenario: str) -> TrendSnapshotResponse | None:
    """Load a scored snapshot from Postgres. Returns None if not found."""
    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row

    from app.contracts.trends import (
        SkillVelocity,
        SourceRef,
        TrendSnapshotMeta,
    )
    from app.core.config import get_settings

    try:
        with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ts.*
                    FROM trend_snapshots ts
                    WHERE ts.snapshot_date = %s
                    ORDER BY ts.skill_id
                    """,
                    (snapshot_date,),
                )
                rows = cur.fetchall()
                if not rows:
                    return None

                # Collect all available dates for meta
                cur.execute(
                    "SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date"
                )
                all_dates = [r["snapshot_date"] for r in cur.fetchall()]

        items: list[SkillVelocity] = []
        for r in rows:
            items.append(
                SkillVelocity(
                    skill_id=r["skill_id"],
                    skill_label=r["skill_id"].replace("-", " ").title(),
                    research_velocity=r["research_velocity"],
                    labor_decay=r["labor_decay"],
                    labor_decay_source_note=r["labor_decay_source_note"],
                    automation_exposure=r["automation_exposure"],
                    velocity_moderate=r["velocity_moderate"],
                    velocity_fast=r["velocity_fast"],
                    direction_moderate=r["direction_moderate"],
                    direction_fast=r["direction_fast"],
                )
            )

        meta = TrendSnapshotMeta(
            sources=[
                SourceRef(
                    name="arXiv cs.AI RSS",
                    url="https://rss.arxiv.org/rss/cs.AI",
                    retrieved_at=snapshot_date,
                ),
                SourceRef(
                    name="BLS Occupational Projections 2023-2033",
                    url=(
                        "https://www.bls.gov/emp/tables/"
                        "occupational-projections-and-characteristics.htm"
                    ),
                    retrieved_at=snapshot_date,
                ),
            ],
            snapshot_date=snapshot_date,
            scenario=scenario,  # type: ignore[arg-type]
            is_estimate=True,
            weights={"research_velocity": 0.6, "labor_decay": 0.4},
            labor_decay_is_static=True,
            available_snapshots=all_dates,
        )
        return TrendSnapshotResponse(meta=meta, items=items)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def list_available_dates() -> list[date]:
    """Return all snapshot dates, from DB if available, else from mock."""
    if _db_available():
        dates = _list_snapshot_dates_db()
        if dates:
            return dates
    return [date.fromisoformat(d) for d in ["2026-10-13", "2026-10-20"]]


def get_snapshot(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
    """
    Return a TrendSnapshotResponse.
    Falls back to the mock fixture if no live data is available.
    """
    if snapshot_date is None:
        available = list_available_dates()
        snapshot_date = available[-1] if available else date.today()

    if _db_available():
        result = _load_snapshot_db(snapshot_date, scenario)
        if result is not None:
            return result

    # Fallback: mock fixture
    return mocks.snapshot(scenario)


# ---------------------------------------------------------------------------
# Legacy data access (kept for backward compat with existing tests)
# ---------------------------------------------------------------------------


def list_signals(scenario: ScenarioId) -> list[TrendSignal]:
    return mocks.signals(scenario)


def get_signal(
    entity_type: EntityType | None, entity_id: str, scenario: ScenarioId
) -> TrendSignal | None:
    return next(
        (
            s
            for s in mocks.signals(scenario)
            if (entity_type is None or s.entity_type == entity_type) and s.entity_id == entity_id
        ),
        None,
    )
