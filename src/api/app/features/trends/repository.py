"""Data access layer for trend snapshots.

Strategy:
  1. Try Postgres (trend_snapshots table, written by score.py).
  2. Fall back to mock fixture (mock_trends.json) if DB is unavailable or
     has no data yet — so the endpoint is always callable in demo mode.

No network calls are made here; arXiv and BLS data are pre-fetched by the
pipeline scripts (Part 5 and Part 3 respectively).
"""

from __future__ import annotations

import time
from datetime import date
from typing import Literal

from app.contracts.common import ScenarioId
from app.contracts.trends import EntityType, TrendSignal, TrendSnapshotResponse
from app.core.errors import NotFoundError
from app.features.trends import mocks

# ---------------------------------------------------------------------------
# Source resolution & DB availability (short-TTL negative cache)
# ---------------------------------------------------------------------------

SourceType = Literal["db", "fixture"]

_db_status_cache: tuple[bool, float] | None = None
DB_FAILED_RETRY_TTL_S: float = 5.0


def _reset_db_cache() -> None:
    """Reset DB availability cache (used by unit tests to simulate recovery)."""
    global _db_status_cache
    _db_status_cache = None


def _db_available() -> bool:
    """Check if Postgres is reachable with short-TTL negative caching.

    - Successful checks are cached indefinitely for process lifetime.
    - Failed checks are cached only for DB_FAILED_RETRY_TTL_S (5s), allowing
      transient container startup races to recover automatically.
    """
    global _db_status_cache
    now = time.monotonic()
    if _db_status_cache is not None:
        status, timestamp = _db_status_cache
        if status:
            return True
        if now - timestamp < DB_FAILED_RETRY_TTL_S:
            return False

    try:
        from app.core.config import get_settings

        db_url = get_settings().database_url
        if not db_url:
            _db_status_cache = (False, now)
            return False

        from app.core.db import database_status

        is_ok = database_status() == "ok"
        _db_status_cache = (is_ok, now)
        return is_ok
    except Exception:
        _db_status_cache = (False, now)
        return False


def resolve_source() -> SourceType:
    """Decide authoritatively whether requests should be served from DB or fixtures.

    Rule: Use 'db' ONLY if the database is reachable AND trend_snapshots has at
    least one row. If the DB is unreachable OR reachable-but-empty, resolve to
    'fixture'.
    """
    if not _db_available():
        return "fixture"
    dates = _list_snapshot_dates_db()
    if not dates:
        return "fixture"
    return "db"


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
            data_provenance_note=("Measured from arXiv cs.AI query API historical date windows."),
        )
        return TrendSnapshotResponse(meta=meta, items=items)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def list_available_dates(source: SourceType | None = None) -> list[date]:
    """Return all snapshot dates for the authoritative source."""
    if source is None:
        source = resolve_source()
    if source == "db":
        return _list_snapshot_dates_db()
    return list(mocks.AVAILABLE_MOCK_DATES)


def get_snapshot(
    snapshot_date: date | None,
    scenario: str,
    source: SourceType | None = None,
) -> TrendSnapshotResponse:
    """Return a TrendSnapshotResponse from the authoritative source.

    Both list_available_dates and get_snapshot use the exact same resolved source,
    guaranteeing they never disagree (e.g. empty DB resolves to fixture for both).
    """
    if source is None:
        source = resolve_source()

    available = list_available_dates(source=source)
    if snapshot_date is None:
        snapshot_date = available[-1] if available else date.today()

    if snapshot_date not in available:
        raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")

    if source == "db":
        result = _load_snapshot_db(snapshot_date, scenario)
        if result is not None:
            return result
        raise NotFoundError(f"Snapshot for date {snapshot_date.isoformat()} not found")

    # Fallback: date-aware mock fixture
    return mocks.snapshot(scenario, snapshot_date)


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
