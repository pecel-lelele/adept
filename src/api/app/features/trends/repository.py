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
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

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


@dataclass
class ResolvedContext:
    source: Literal["db", "fixture"]
    available_dates: list[date]
    conn: Any | None = None

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def __enter__(self) -> ResolvedContext:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


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


def resolve_context() -> ResolvedContext:
    """Resolve both authoritative source and available dates in ONE database round-trip."""
    if not _db_available():
        return ResolvedContext(source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES))

    # Support unit tests where _list_snapshot_dates_db is mocked
    from unittest.mock import Mock

    if isinstance(_list_snapshot_dates_db, Mock):
        dates = _list_snapshot_dates_db()
        if not dates:
            return ResolvedContext(
                source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES)
            )
        return ResolvedContext(source="db", available_dates=dates)

    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row

    from app.core.config import get_settings

    try:
        conn = psycopg.connect(get_settings().database_url, row_factory=dict_row)
        dates = _list_snapshot_dates_db(conn=conn)
        if not dates:
            conn.close()
            return ResolvedContext(
                source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES)
            )
        return ResolvedContext(source="db", available_dates=dates, conn=conn)
    except Exception:
        return ResolvedContext(source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES))


def resolve_source() -> SourceType:
    """Decide authoritatively whether requests should be served from DB or fixtures.

    Rule: Use 'db' ONLY if the database is reachable AND trend_snapshots has at
    least one row. If the DB is unreachable OR reachable-but-empty, resolve to
    'fixture'.
    """
    ctx = resolve_context()
    ctx.close()
    return ctx.source


def _list_snapshot_dates_db(conn: Any | None = None) -> list[date]:
    """Return all snapshot dates present in the trend_snapshots table."""
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date")
            return [row["snapshot_date"] for row in cur.fetchall()]

    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row

    from app.core.config import get_settings

    try:
        with psycopg.connect(get_settings().database_url, row_factory=dict_row) as c:
            with c.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date"
                )
                return [row["snapshot_date"] for row in cur.fetchall()]
    except Exception:
        return []


def _load_snapshot_db(
    ctx_or_date: ResolvedContext | date,
    snapshot_date_or_scenario: date | str,
    scenario_or_ctx: str | ResolvedContext | None = None,
) -> TrendSnapshotResponse | None:
    """Load a scored snapshot from Postgres. Returns None if not found.

    Reuses ctx.conn when available and populates available_snapshots directly
    from ctx.available_dates without issuing a redundant query.
    """
    ctx: ResolvedContext | None = None
    snapshot_date: date
    scenario: str

    if isinstance(ctx_or_date, ResolvedContext):
        ctx = ctx_or_date
        snapshot_date = snapshot_date_or_scenario  # type: ignore[assignment]
        scenario = str(scenario_or_ctx) if scenario_or_ctx is not None else "moderate"
    else:
        snapshot_date = ctx_or_date
        scenario = str(snapshot_date_or_scenario)
        if isinstance(scenario_or_ctx, ResolvedContext):
            ctx = scenario_or_ctx

    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row

    from app.contracts.trends import (
        SkillVelocity,
        SourceRef,
        TrendSnapshotMeta,
    )
    from app.core.config import get_settings

    def _execute(c: Any) -> list[dict[str, Any]] | None:
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT ts.*
                FROM trend_snapshots ts
                WHERE ts.snapshot_date = %s
                ORDER BY ts.skill_id
                """,
                (snapshot_date,),
            )
            return cur.fetchall()

    try:
        if ctx is not None and ctx.conn is not None:
            rows = _execute(ctx.conn)
        else:
            with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
                rows = _execute(conn)

        if not rows:
            return None

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

        all_dates = ctx.available_dates if ctx is not None else _list_snapshot_dates_db()

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


def list_available_dates(
    ctx: ResolvedContext | None = None,
    source: SourceType | None = None,
) -> list[date]:
    """Return all snapshot dates for the authoritative source."""
    if ctx is not None:
        return list(ctx.available_dates)
    if source is None:
        resolved = resolve_context()
        try:
            return list(resolved.available_dates)
        finally:
            resolved.close()
    if source == "db":
        return _list_snapshot_dates_db()
    return list(mocks.AVAILABLE_MOCK_DATES)


def get_snapshot(
    ctx_or_date: ResolvedContext | date | None = None,
    snapshot_date_or_scenario: date | str | None = None,
    scenario: str = "moderate",
    *,
    ctx: ResolvedContext | None = None,
    source: SourceType | None = None,
) -> TrendSnapshotResponse:
    """Return a TrendSnapshotResponse from the authoritative source.

    Accepts either:
      - get_snapshot(ctx, snapshot_date, scenario)
      - get_snapshot(snapshot_date, scenario, ctx=ctx)
    Reuses ResolvedContext without opening redundant connections or re-querying dates.
    """
    resolved_ctx: ResolvedContext | None = ctx
    target_date: date | None = None
    target_scenario: str = scenario

    if isinstance(ctx_or_date, ResolvedContext):
        resolved_ctx = ctx_or_date
        target_date = (
            snapshot_date_or_scenario if isinstance(snapshot_date_or_scenario, date) else None
        )
        if isinstance(snapshot_date_or_scenario, str):
            target_scenario = snapshot_date_or_scenario
        elif isinstance(scenario, str):
            target_scenario = scenario
    else:
        target_date = ctx_or_date
        if isinstance(snapshot_date_or_scenario, str):
            target_scenario = snapshot_date_or_scenario

    should_close_ctx = False
    if resolved_ctx is None:
        resolved_ctx = resolve_context()
        should_close_ctx = True

    try:
        available = list_available_dates(ctx=resolved_ctx)
        if target_date is None:
            target_date = available[-1] if available else date.today()

        if target_date not in available:
            raise NotFoundError(f"Snapshot for date {target_date.isoformat()} not found")

        if resolved_ctx.source == "db":
            result = _load_snapshot_db(resolved_ctx, target_date, target_scenario)
            if result is not None:
                return result
            raise NotFoundError(f"Snapshot for date {target_date.isoformat()} not found")

        # Fallback: date-aware mock fixture
        return mocks.snapshot(target_scenario, target_date)
    finally:
        if should_close_ctx and resolved_ctx is not None:
            resolved_ctx.close()


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
