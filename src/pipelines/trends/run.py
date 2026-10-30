"""F2 scheduled trend refresh (owner M1): ingest → score → validate → publish.

    PYTHONPATH=src/api:src python -m pipelines.trends.run [--skip-ingest] [--dry-run]

1. Ingest (``arxiv_ingest``): today's arXiv cs.AI listing → sentence-level mention counts per
   skill (all-MiniLM-L6-v2) → ``skill_signal_raw`` for this ISO week. Skipped with
   ``--skip-ingest`` (rescore what is already stored).
2. Score (``score.score_rows``): latest week t1 against the week before t0, blended with the
   BLS labour baseline and the moderate / fast scenario transform.
3. Validate: two distinct weeks, enough skills, every skill in the taxonomy, every number
   finite, a known direction label. A snapshot that fails is never written.
4. Publish: the snapshot rows and their provenance (sources, measured week) in one
   transaction, so the API sees the whole new snapshot or keeps the previous one.

A failed run exits non-zero and changes nothing: the last valid snapshot stays live and the
Radar keeps showing its own date and measured period, so its age is visible.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from contextlib import nullcontext
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ARXIV_RSS_URL = "https://rss.arxiv.org/rss/cs.AI"
BLS_URL = "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm"
BLS_RETRIEVED_AT = "2026-10-20"  # recorded acquisition of the versioned static baseline
MIN_SKILLS = 50  # a snapshot covering fewer skills is treated as a broken run
DIRECTIONS = {"rising", "stable", "declining"}
NUMERIC = (
    "research_velocity",
    "labor_decay",
    "automation_exposure",
    "velocity_moderate",
    "velocity_fast",
)


def week_bounds(period: str) -> tuple[date, date]:
    """'2026-W42' → (Monday, Sunday) of that ISO week."""
    year, week = period.split("-W")
    monday = date.fromisocalendar(int(year), int(week), 1)
    return monday, monday + timedelta(days=6)


def validate(rows: list[dict], known_ids: set[str], t0: str, t1: str) -> list[str]:
    """Reasons this snapshot must not be published (empty list = valid)."""
    errors: list[str] = []
    if t0 == t1:
        errors.append(f"only one week of signals ({t1}); need two to measure change")
    if len(rows) < MIN_SKILLS:
        errors.append(f"{len(rows)} skills scored; expected at least {MIN_SKILLS}")
    unknown = sorted({r["skill_id"] for r in rows} - known_ids)
    if unknown:
        errors.append(f"skills not in the taxonomy: {unknown[:5]}")
    for r in rows:
        bad = [k for k in NUMERIC if not math.isfinite(float(r.get(k, math.nan)))]
        if bad:
            errors.append(f"{r['skill_id']}: non-finite {bad}")
        if (
            r.get("direction_moderate") not in DIRECTIONS
            or r.get("direction_fast") not in DIRECTIONS
        ):
            errors.append(f"{r['skill_id']}: unknown direction label")
    return errors


DateRange = tuple[date, date]


def provenance(
    t0: str, t1: str, t0_dates: DateRange, t1_dates: DateRange
) -> tuple[list[dict], str]:
    """Sources and a note naming the days actually collected first (read back as
    observed_from/to). Dates come from the stored signals, never the calendar week, so a run
    early in a week does not claim days that have not happened yet."""
    start, end = t1_dates
    base_start, base_end = t0_dates
    note = (
        f"Scored by pipelines.trends.run from arXiv cs.AI listing mentions collected "
        f"{start.isoformat()}..{end.isoformat()} ({t1}) against "
        f"{base_start.isoformat()}..{base_end.isoformat()} ({t0}), blended with the BLS "
        "2023-2033 projections as the labour baseline."
    )
    retrieved = end.isoformat()
    sources = [
        {"name": "arXiv cs.AI listing", "url": ARXIV_RSS_URL, "retrieved_at": retrieved},
        {
            "name": "BLS Occupational Projections 2023-2033",
            "url": BLS_URL,
            "retrieved_at": BLS_RETRIEVED_AT,
        },
    ]
    return sources, note


def collected_dates(db_url: str, period: str | None = None) -> DateRange | None:
    """First and last day arXiv signals were collected (for one ISO week, or overall)."""
    import psycopg  # type: ignore[import]

    where = "source = 'arxiv' AND metric = 'mention_count'" + (" AND period = %s" if period else "")
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT min(retrieved_at), max(retrieved_at) FROM skill_signal_raw WHERE {where}",
            (period,) if period else (),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row and row[0] and row[1] else None


def publish(
    rows: list[dict],
    snapshot_date: date,
    sources: list[dict],
    note: str,
    db_url: str,
    *,
    conn: Any = None,
) -> None:
    """Write the snapshot and its provenance in one transaction.

    Deletes all existing rows for snapshot_date before inserting so that a
    rescore never leaves stale rows from a previous run that would inflate
    role coverage and suppress uncertainty widening.
    """
    import psycopg  # type: ignore[import]

    managed = nullcontext(conn) if conn is not None else psycopg.connect(db_url)
    with managed as conn, conn.transaction(), conn.cursor() as cur:
        # Snapshot cleanup: remove any stale rows from a previous run on this date.
        cur.execute(
            "DELETE FROM trend_snapshots WHERE snapshot_date = %s",
            (snapshot_date,),
        )
        for r in rows:
            cur.execute(
                """
                INSERT INTO trend_snapshots
                    (skill_id, snapshot_date, research_velocity, labor_decay,
                     labor_decay_source_note, automation_exposure, velocity_moderate,
                     velocity_fast, direction_moderate, direction_fast)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (skill_id, snapshot_date) DO UPDATE SET
                    research_velocity = EXCLUDED.research_velocity,
                    labor_decay = EXCLUDED.labor_decay,
                    labor_decay_source_note = EXCLUDED.labor_decay_source_note,
                    automation_exposure = EXCLUDED.automation_exposure,
                    velocity_moderate = EXCLUDED.velocity_moderate,
                    velocity_fast = EXCLUDED.velocity_fast,
                    direction_moderate = EXCLUDED.direction_moderate,
                    direction_fast = EXCLUDED.direction_fast
                """,
                (
                    r["skill_id"],
                    snapshot_date,
                    r["research_velocity"],
                    r["labor_decay"],
                    r["labor_decay_source_note"],
                    r["automation_exposure"],
                    r["velocity_moderate"],
                    r["velocity_fast"],
                    r["direction_moderate"],
                    r["direction_fast"],
                ),
            )
        cur.execute(
            """
            INSERT INTO trend_snapshot_meta (snapshot_date, sources, provenance_note)
            VALUES (%s, %s, %s)
            ON CONFLICT (snapshot_date) DO UPDATE
                SET sources = EXCLUDED.sources, provenance_note = EXCLUDED.provenance_note,
                    loaded_at = now()
            """,
            (snapshot_date, json.dumps(sources), note),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the trend snapshot (F2).")
    parser.add_argument("--skip-ingest", action="store_true", help="rescore stored signals only")
    parser.add_argument("--dry-run", action="store_true", help="validate but do not publish")
    parser.add_argument("--snapshot-date", default=None, help="Must equal the measured end date")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings
    from pipelines.trends import arxiv_ingest, score

    db_url = get_settings().database_url

    if not args.skip_ingest:
        arxiv_ingest.main()
        # An empty or unreadable feed returns normally without storing anything; refuse to
        # republish older signals as if they were new.
        latest = collected_dates(db_url)
        if latest is None or latest[1] != date.today():
            print(
                "ERROR: the ingest stored no new arXiv signals today; nothing published. "
                "The previous snapshot stays live.",
                file=sys.stderr,
            )
            return 1

    periods = score.list_available_periods(db_url)
    if not periods:
        print("ERROR: no arXiv signals stored; nothing published.", file=sys.stderr)
        return 1
    t1 = periods[-1]
    t0 = periods[-2] if len(periods) > 1 else t1
    counts_t0, total_t0 = score.load_signal_raw(db_url, t0)
    counts_t1, total_t1 = score.load_signal_raw(db_url, t1)
    exposure = score.load_automation_exposure()
    # Issue 2 fix: load the full DB catalogue so score_rows covers every skill,
    # and so validate uses the same authoritative ID set as the rest of the application.
    skill_ids = score.load_skill_ids(db_url)
    rows = score.score_rows(
        counts_t0,
        total_t0,
        counts_t1,
        total_t1,
        score.load_labor_decay(),
        exposure,
        skill_ids=skill_ids,
    )
    # Issue 3 fix: only validate and publish rows that have real signal; catalogue-only
    # default rows (has_evidence=False) must not enter trend_snapshots or inflate coverage.
    evidenced = [r for r in rows if r.get("has_evidence", True)]

    errors = validate(evidenced, skill_ids, t0, t1)
    if errors:
        print("Snapshot NOT published; the previous snapshot stays live:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    t0_dates, t1_dates = collected_dates(db_url, t0), collected_dates(db_url, t1)
    if t0_dates is None or t1_dates is None:
        print("ERROR: signal collection dates missing; nothing published.", file=sys.stderr)
        return 1
    sources, note = provenance(t0, t1, t0_dates, t1_dates)
    snapshot_date = t1_dates[1]
    if args.snapshot_date and date.fromisoformat(args.snapshot_date) != snapshot_date:
        print("ERROR: snapshot date must equal the actual measured end date.", file=sys.stderr)
        return 1
    rising = sum(1 for r in evidenced if r["direction_moderate"] == "rising")
    print(f"Valid snapshot {snapshot_date}: {len(evidenced)} skills, {rising} rising. {note}")
    if args.dry_run:
        print("Dry run: nothing published.")
        return 0
    publish(evidenced, snapshot_date, sources, note, db_url)
    print(f"Published snapshot {snapshot_date}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
