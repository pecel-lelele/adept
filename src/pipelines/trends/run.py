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
    t0: str,
    t1: str,
    t0_dates: DateRange,
    t1_dates: DateRange,
    *,
    retrieval: dict[str, object],
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
    sources = [
        {
            "name": "arXiv cs.AI listing",
            "url": ARXIV_RSS_URL,
            **{
                key: retrieval[key]
                for key in ("retrieved_at", "retrieved_at_basis", "retrieval_evidence")
            },
        },
        {
            "name": "BLS Occupational Projections 2023-2033",
            "url": BLS_URL,
            **bls_retrieval(),
        },
    ]
    return sources, note


def bls_retrieval() -> dict[str, str]:
    """Recorded acquisition of the versioned static BLS baseline (sidecar evidence).

    Dated by the last commit that changed the CSV's bytes, never by later moves.
    """
    from pipelines.trends.provenance import cached_retrieval

    return cached_retrieval(REPO_ROOT / "src/data/seed/labor_decay.csv")


def collected_dates(db_url: str, period: str | None = None) -> DateRange | None:
    """First and last day arXiv signals were collected (for one ISO week, or overall)."""
    import psycopg  # type: ignore[import]

    # Replay provenance fix: only proven live observations may form a refresh baseline.
    where = (
        "source = 'arxiv' AND metric = 'mention_count' AND is_replay IS FALSE "
        "AND retrieved_at_basis IN ('pipeline_fetch', 'fetch_log')"
        + (" AND period = %s" if period else "")
    )
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT min(observation_window_start), max(observation_window_end) "
            f"FROM skill_signal_raw WHERE {where}",
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
    provenance: dict[str, object] | None = None,
    conn: Any = None,
) -> None:
    """Write the snapshot and its provenance in one transaction.

    Deletes all existing rows for snapshot_date before inserting so that a
    rescore never leaves stale rows from a previous run that would inflate
    role coverage and suppress uncertainty widening.
    """
    import psycopg  # type: ignore[import]

    from app.features.trends.provenance import PROVENANCE_FIELDS, lock_snapshot, provenance_values

    facts = provenance_values(provenance or {}, note)

    owned = conn is None
    managed = psycopg.connect(db_url) if owned else nullcontext(conn)
    # An injected connection's caller owns the transaction and its deadline/lease checks;
    # a connection created here gets its own explicit transaction.
    with (
        managed as conn,
        conn.transaction() if owned else nullcontext(),
        conn.cursor() as cur,
    ):
        lock_snapshot(conn, snapshot_date)
        cur.execute(
            "SELECT is_replay FROM trend_snapshot_meta WHERE snapshot_date = %s FOR UPDATE",
            (snapshot_date,),
        )
        previous = cur.fetchone()
        if previous and previous[0] is not None and previous[0] != facts["is_replay"]:
            raise ValueError("A published live/replay slot cannot change origin")
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
                     velocity_fast, direction_moderate, direction_fast,
                     is_replay, observation_window_start, observation_window_end,
                     retrieved_at, retrieved_at_basis, retrieval_evidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    *(facts[field] for field in PROVENANCE_FIELDS),
                ),
            )
        cur.execute(
            """
            INSERT INTO trend_snapshot_meta (snapshot_date, sources, provenance_note,
                is_replay, observation_window_start, observation_window_end,
                retrieved_at, retrieved_at_basis, retrieval_evidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (snapshot_date) DO UPDATE
                SET sources = EXCLUDED.sources, provenance_note = EXCLUDED.provenance_note,
                    loaded_at = now(), is_replay = EXCLUDED.is_replay,
                    observation_window_start = EXCLUDED.observation_window_start,
                    observation_window_end = EXCLUDED.observation_window_end,
                    retrieved_at = EXCLUDED.retrieved_at,
                    retrieved_at_basis = EXCLUDED.retrieved_at_basis,
                    retrieval_evidence = EXCLUDED.retrieval_evidence
            """,
            (
                snapshot_date,
                json.dumps(sources, default=str),
                note,
                *(facts[field] for field in PROVENANCE_FIELDS),
            ),
        )


def live_provenance(db_url: str, period: str) -> dict[str, object]:
    """Read the live source's stored evidence, independently of its publication date."""
    import psycopg

    with psycopg.connect(db_url) as conn:
        row = conn.execute(
            "SELECT min(observation_window_start), max(observation_window_end), "
            "max(retrieved_at), string_agg(DISTINCT retrieval_evidence, '; '), "
            "(array_agg(retrieved_at_basis ORDER BY retrieved_at DESC))[1] "
            "FROM skill_signal_raw WHERE source = 'arxiv' AND metric = 'mention_count' "
            "AND period = %s AND is_replay IS FALSE "
            "AND retrieved_at_basis IN ('pipeline_fetch', 'fetch_log')",
            (period,),
        ).fetchone()
    if not row or any(value is None for value in row):
        raise ValueError("Live refresh lacks verified source provenance")
    return {
        "is_replay": False,
        "observation_window_start": row[0],
        "observation_window_end": row[1],
        "retrieved_at": row[2],
        "retrieved_at_basis": row[4],
        "retrieval_evidence": row[3],
    }


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
    facts = live_provenance(db_url, t1)
    sources, note = provenance(t0, t1, t0_dates, t1_dates, retrieval=facts)
    snapshot_date = t1_dates[1]
    if args.snapshot_date and date.fromisoformat(args.snapshot_date) != snapshot_date:
        print("ERROR: snapshot date must equal the actual measured end date.", file=sys.stderr)
        return 1
    rising = sum(1 for r in evidenced if r["direction_moderate"] == "rising")
    print(f"Valid snapshot {snapshot_date}: {len(evidenced)} skills, {rising} rising. {note}")
    if args.dry_run:
        print("Dry run: nothing published.")
        return 0
    publish(evidenced, snapshot_date, sources, note, db_url, provenance=facts)
    print(f"Published snapshot {snapshot_date}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
