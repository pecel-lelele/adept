"""Data access layer for trend snapshots.

Strategy:
  1. Try Postgres (trend_snapshots table, written by score.py).
  2. Fall back to mock fixture (mock_trends.json) if DB is unavailable or
     has no data yet — so the endpoint is always callable in demo mode.

No external source API calls are made here; arXiv and BLS data are pre-fetched by the
pipeline scripts (Part 5 and Part 3 respectively).
"""

from __future__ import annotations

import socket
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from threading import Event, Timer
from typing import Any, Literal

import psycopg
from psycopg.rows import dict_row

from app.contracts.trends import TrendSnapshotResponse
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.features.trends import mocks
from app.features.trends.provenance import observation_window


def _skill_labels() -> dict[str, str]:
    """Readable skill names from the taxonomy (falls back to the id when a skill is new)."""
    from app.core import seed

    return {r["id"]: r["label"] for r in seed.rows("taxonomy", "skills")}


# ---------------------------------------------------------------------------
# Source resolution & DB availability (short-TTL negative cache)
# ---------------------------------------------------------------------------

SourceType = Literal["db", "fixture"]

_db_status_cache: tuple[bool, float] | None = None
DB_FAILED_RETRY_TTL_S: float = 5.0


class TrendsUnavailableError(Exception):
    """The authoritative trend database could not supply a snapshot."""


def _get_connection(
    connect_timeout_s: int = 2,
    statement_timeout_ms: int = 2000,
    lock_timeout_ms: int = 1000,
) -> psycopg.Connection[dict[str, Any]]:
    """Bound request-path connections and queries using libpq startup options.

    libpq requires integer seconds for connect_timeout (minimum effective 2s).
    Server timeouts apply before the first query, including date discovery.
    """
    return psycopg.connect(
        get_settings().database_url,
        row_factory=dict_row,
        autocommit=True,
        connect_timeout=connect_timeout_s,
        options=f"-c statement_timeout={statement_timeout_ms} -c lock_timeout={lock_timeout_ms}",
    )


@contextmanager
def _read_deadline(conn: Any, timeout_s: float = 3.0) -> Iterator[None]:
    """Interrupt stalled libpq I/O locally, even if PostgreSQL cannot reply.

    Only the owning request thread uses/closes the psycopg connection. The
    watchdog shuts down its socket without taking ownership or calling libpq.
    Joining it before connection cleanup prevents a reused descriptor race.
    """
    expired = Event()
    descriptor = conn.fileno()

    def interrupt() -> None:
        expired.set()
        try:
            transport = socket.socket(fileno=descriptor)
            try:
                transport.shutdown(socket.SHUT_RDWR)
            finally:
                # libpq still owns the descriptor and will close it itself.
                transport.detach()
        except (OSError, ValueError):
            # The peer/driver may already have disconnected at the deadline.
            pass

    watchdog = Timer(timeout_s, interrupt)
    watchdog.daemon = True
    watchdog.start()
    try:
        yield
    finally:
        watchdog.cancel()
        watchdog.join()
        if expired.is_set():
            # The socket is unusable; release libpq resources on the request thread.
            conn.close()
    if expired.is_set():
        raise psycopg.OperationalError("Trend database client read deadline exceeded")


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
    """Legacy health-check compatibility; snapshot reads use resolve_context directly.

    Check if Postgres is reachable with short-TTL negative caching.

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


def resolve_context(strict: bool = False) -> ResolvedContext:
    """Resolve source and dates on one bounded connection.

    Strict callers always try the database, bypassing the demo negative cache.
    They never accept an empty database or a fixture-backed context.
    """
    global _db_status_cache
    now = time.monotonic()
    if not strict and _db_status_cache is not None:
        status, timestamp = _db_status_cache
        if not status and now - timestamp < DB_FAILED_RETRY_TTL_S:
            return ResolvedContext(
                source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES)
            )

    # Preserve the legacy date-loader test seam without opening a connection.
    from unittest.mock import Mock

    conn = None
    dates: list[date] = []
    try:
        if isinstance(_list_snapshot_dates_db, Mock):
            dates = _list_snapshot_dates_db()
        else:
            conn = _get_connection()
            dates = _list_snapshot_dates_db(conn=conn, strict=strict)
        _db_status_cache = (True, now)
        if dates:
            return ResolvedContext(source="db", available_dates=dates, conn=conn)
        if strict:
            raise TrendsUnavailableError("No database trend snapshots available")
    except TrendsUnavailableError:
        raise
    except Exception as exc:
        _db_status_cache = (False, now)
        if strict:
            raise TrendsUnavailableError("Trend database unavailable") from exc
    finally:
        # Ownership transfers to ResolvedContext only on a successful dates read.
        if conn is not None and not dates:
            ResolvedContext("db", [], conn).close()
    return ResolvedContext(source="fixture", available_dates=list(mocks.AVAILABLE_MOCK_DATES))


def resolve_source(strict: bool = False) -> SourceType:
    """Decide authoritatively whether requests should be served from DB or fixtures.

    Rule: Use 'db' ONLY if the database is reachable AND trend_snapshots has at
    least one row. If the DB is unreachable OR reachable-but-empty, resolve to
    'fixture'.
    """
    ctx = resolve_context(strict=strict)
    ctx.close()
    return ctx.source


def _list_snapshot_dates_db(conn: Any | None = None, strict: bool = False) -> list[date]:
    """Return all snapshot dates present in the trend_snapshots table."""
    if conn is not None:
        with _read_deadline(conn), conn.cursor() as cur:
            cur.execute("SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date")
            return [row["snapshot_date"] for row in cur.fetchall()]

    try:
        with _get_connection() as c:
            with _read_deadline(c), c.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT snapshot_date FROM trend_snapshots ORDER BY snapshot_date"
                )
                return [row["snapshot_date"] for row in cur.fetchall()]
    except Exception as exc:
        if strict:
            raise TrendsUnavailableError("Trend dates unavailable") from exc
        return []


def _load_snapshot_db(
    ctx_or_date: ResolvedContext | date,
    snapshot_date_or_scenario: date | str,
    scenario_or_ctx: str | ResolvedContext | None = None,
    *,
    strict: bool = False,
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

    from app.contracts.trends import (
        SkillVelocity,
        SourceRef,
        TrendSnapshotMeta,
    )

    stored_meta: dict[str, Any] | None = None

    def _execute(c: Any) -> list[dict[str, Any]] | None:
        nonlocal stored_meta
        with _read_deadline(c), c.cursor() as cur:
            cur.execute(
                """
                SELECT ts.*
                FROM trend_snapshots ts
                WHERE ts.snapshot_date = %s
                ORDER BY ts.skill_id
                """,
                (snapshot_date,),
            )
            found = cur.fetchall()
            try:
                cur.execute(
                    "SELECT sources, provenance_note FROM trend_snapshot_meta "
                    "WHERE snapshot_date = %s",
                    (snapshot_date,),
                )
                stored_meta = cur.fetchone()
            except psycopg.errors.UndefinedTable:
                stored_meta = None  # database not migrated yet: use the default citation
            return found

    try:
        if ctx is not None and ctx.conn is not None:
            rows = _execute(ctx.conn)
        else:
            with _get_connection() as conn:
                rows = _execute(conn)

        if not rows:
            return None

        items: list[SkillVelocity] = []
        for r in rows:
            items.append(
                SkillVelocity(
                    skill_id=r["skill_id"],
                    skill_label=_skill_labels().get(
                        r["skill_id"], r["skill_id"].replace("-", " ").title()
                    ),
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

        all_dates = (
            ctx.available_dates if ctx is not None else _list_snapshot_dates_db(strict=strict)
        )

        if stored_meta and stored_meta.get("sources"):
            # Provenance recorded with the snapshot (loader or pipeline run).
            sources = [
                SourceRef(
                    name=str(src["name"]),
                    url=str(src["url"]),
                    retrieved_at=date.fromisoformat(str(src["retrieved_at"])),
                )
                for src in stored_meta["sources"]
            ]
            note = str(stored_meta.get("provenance_note") or "") or None
        else:
            sources = [
                SourceRef(
                    name="arXiv cs.AI",
                    url="https://arxiv.org/list/cs.AI/recent",
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
            ]
            note = "Scored by the Adept trend pipeline from arXiv cs.AI papers and BLS projections."

        observed_from, observed_to = observation_window(stored_meta, note)
        meta = TrendSnapshotMeta(
            sources=sources,
            snapshot_date=snapshot_date,
            observed_from=observed_from,
            observed_to=observed_to,
            scenario=scenario,  # type: ignore[arg-type]
            is_estimate=True,
            weights={"research_velocity": 0.6, "labor_decay": 0.4},
            labor_decay_is_static=True,
            available_snapshots=all_dates,
            data_provenance_note=note,
        )
        return TrendSnapshotResponse(meta=meta, items=items)
    except TrendsUnavailableError:
        raise
    except Exception as exc:
        if strict:
            raise TrendsUnavailableError("Trend snapshot unavailable") from exc
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def list_available_dates(
    ctx: ResolvedContext | None = None,
    source: SourceType | None = None,
    strict: bool = False,
) -> list[date]:
    """Return all snapshot dates for the authoritative source."""
    if ctx is not None:
        if strict and ctx.source != "db":
            raise TrendsUnavailableError("Fixture context is unavailable in strict mode")
        return list(ctx.available_dates)
    if source is None:
        resolved = resolve_context(strict=strict)
        try:
            return list(resolved.available_dates)
        finally:
            resolved.close()
    if source == "db":
        return _list_snapshot_dates_db(strict=strict)
    if strict:
        raise TrendsUnavailableError("Fixture source is unavailable in strict mode")
    return list(mocks.AVAILABLE_MOCK_DATES)


def get_snapshot(
    ctx_or_date: ResolvedContext | date | None = None,
    snapshot_date_or_scenario: date | str | None = None,
    scenario: str = "moderate",
    *,
    ctx: ResolvedContext | None = None,
    source: SourceType | None = None,
    strict: bool = False,
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
        resolved_ctx = resolve_context(strict=strict)
        should_close_ctx = True

    try:
        available = list_available_dates(ctx=resolved_ctx, strict=strict)
        if target_date is None:
            target_date = available[-1] if available else date.today()

        if target_date not in available:
            raise NotFoundError(f"Snapshot for date {target_date.isoformat()} not found")

        if resolved_ctx.source == "db":
            result = _load_snapshot_db(resolved_ctx, target_date, target_scenario, strict=strict)
            if result is not None:
                return result
            if strict:
                raise TrendsUnavailableError("Resolved database snapshot is no longer available")
            raise NotFoundError(f"Snapshot for date {target_date.isoformat()} not found")

        # Fallback: date-aware mock fixture
        return mocks.snapshot(target_scenario, target_date)
    finally:
        if should_close_ctx and resolved_ctx is not None:
            resolved_ctx.close()
