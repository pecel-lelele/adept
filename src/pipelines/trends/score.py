"""src/pipelines/trends/score.py

PART 6 – Composite scorer + scenario transform.

Reads:
  skill_signal_raw table     (mention counts from arXiv ingestion)
  src/data/seed/labor_decay.csv
  src/data/seed/canonical_skills.csv  (for automation_exposure)

Writes:
  trend_snapshots table      (one row per skill × snapshot_date)

Scoring formula (all deterministic arithmetic, no ML training):

    freq(s, t)     = count(s, t) / total_papers(t)
    RV(s, t0, t1)  = ln((freq(s, t1) + eps) / (freq(s, t0) + eps))   # eps = 1e-4

    V(s)           = 0.6 * RV(s, t0, t1) + 0.4 * labor_decay(s)

    # --- scenario transform ---
    E = automation_exposure(s)
    k = 1.5
    if V(s) < 0:
        V_fast = V(s) * (1 + E * k)            # amplify decline for high-exposure skills
    else:
        V_fast = V(s) * (1 + (1 - E) * k)      # amplify rise for low-exposure skills
    V_fast = clamp(V_fast, -2.0, 2.0)
    V_moderate = V(s)                           # no amplification

    direction(v) = "rising"   if v >  0.05 else
                   "declining" if v < -0.05 else
                   "stable"

Weights used: RV_WEIGHT = 0.6, LABOR_WEIGHT = 0.4, k = 1.5

Run (after arxiv_ingest.py):
  PYTHONPATH=src/api:src uv run --no-project python src/pipelines/trends/score.py

Options:
  --snapshot-date YYYY-MM-DD   (default: today)
  --t0-period     YYYY-Www     (default: week before latest)
  --t1-period     YYYY-Www     (default: latest week in skill_signal_raw)
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
LABOR_DECAY_CSV = SEED_DIR / "labor_decay.csv"
CANONICAL_CSV = SEED_DIR / "canonical_skills.csv"

EPS = 1e-4
RV_WEIGHT = 0.6
LABOR_WEIGHT = 0.4
K = 1.5
V_CLAMP_MIN = -2.0
V_CLAMP_MAX = 2.0
DIRECTION_RISE = 0.05
DIRECTION_DECLINE = -0.05


# ---------------------------------------------------------------------------
# Pure scoring functions (testable without I/O)
# ---------------------------------------------------------------------------


def research_velocity(freq_t0: float, freq_t1: float, eps: float = EPS) -> float:
    """Log-ratio growth of arXiv mention frequency."""
    return math.log((freq_t1 + eps) / (freq_t0 + eps))


def composite_velocity(rv: float, labor_decay: float) -> float:
    """Composite signal: research velocity + labor baseline."""
    return RV_WEIGHT * rv + LABOR_WEIGHT * labor_decay


def scenario_fast(v: float, automation_exposure: float, k: float = K) -> float:
    """Fast-scenario amplification per the spec."""
    if v < 0:
        v_fast = v * (1 + automation_exposure * k)
    else:
        v_fast = v * (1 + (1 - automation_exposure) * k)
    return clamp(v_fast, V_CLAMP_MIN, V_CLAMP_MAX)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def direction(v: float) -> str:
    if v > DIRECTION_RISE:
        return "rising"
    if v < DIRECTION_DECLINE:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_labor_decay() -> dict[str, tuple[float, str]]:
    """Return {skill_id: (labor_decay_fraction, source_note)}."""
    result: dict[str, tuple[float, str]] = {}
    with LABOR_DECAY_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            result[row["skill_id"]] = (float(row["labor_decay"]), row["labor_decay_source_note"])
    return result


def load_automation_exposure() -> dict[str, float]:
    """Return {skill_id: automation_exposure}."""
    result: dict[str, float] = {}
    with CANONICAL_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            result[row["skill_id"]] = float(row["automation_exposure"])
    return result


def load_signal_raw(db_url: str, period: str) -> tuple[dict[str, float], int]:
    """
    Load mention counts from skill_signal_raw for the given ISO-week period.
    Returns ({skill_id: count}, total_papers_in_period).
    total_papers is taken from arxiv_fetch_log for the matching week.
    """
    import psycopg  # type: ignore[import]
    from psycopg.rows import dict_row  # type: ignore[import]

    counts: dict[str, float] = {}
    total = 0
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT skill_id, value FROM skill_signal_raw "
                "WHERE source = 'arxiv' AND metric = 'mention_count' AND period = %s",
                (period,),
            )
            for row in cur.fetchall():
                counts[row["skill_id"]] = float(row["value"])

            # Get total papers from the log (approximate: use max fetch in the period)
            cur.execute(
                "SELECT COALESCE(SUM(paper_count), 0) AS total "
                "FROM arxiv_fetch_log "
                "WHERE to_char(fetch_date, 'IYYY-\"W\"IW') = %s",
                (period,),
            )
            row = cur.fetchone()
            if row:
                total = int(row["total"]) or 1  # avoid div-by-zero
    return counts, max(total, 1)


def list_available_periods(db_url: str) -> list[str]:
    """Return sorted list of ISO-week periods in skill_signal_raw."""
    import psycopg  # type: ignore[import]

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT period FROM skill_signal_raw "
                "WHERE source = 'arxiv' ORDER BY period"
            )
            return [row[0] for row in cur.fetchall()]


def write_snapshots(
    rows: list[dict],
    snapshot_date: date,
    db_url: str,
) -> None:
    """Upsert scored rows into trend_snapshots."""
    import psycopg  # type: ignore[import]

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO trend_snapshots
                        (skill_id, snapshot_date, research_velocity,
                         labor_decay, labor_decay_source_note, automation_exposure,
                         velocity_moderate, velocity_fast,
                         direction_moderate, direction_fast)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (skill_id, snapshot_date) DO UPDATE SET
                        research_velocity       = EXCLUDED.research_velocity,
                        labor_decay             = EXCLUDED.labor_decay,
                        labor_decay_source_note = EXCLUDED.labor_decay_source_note,
                        automation_exposure     = EXCLUDED.automation_exposure,
                        velocity_moderate       = EXCLUDED.velocity_moderate,
                        velocity_fast           = EXCLUDED.velocity_fast,
                        direction_moderate      = EXCLUDED.direction_moderate,
                        direction_fast          = EXCLUDED.direction_fast
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
        conn.commit()
    print(f"[db] Wrote {len(rows)} snapshot rows for {snapshot_date}.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(
    snapshot_date: date | None = None,
    t0_period: str | None = None,
    t1_period: str | None = None,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings  # noqa: E402

    db_url = get_settings().database_url
    if snapshot_date is None:
        snapshot_date = date.today()

    periods = list_available_periods(db_url)
    if len(periods) < 1:
        print(
            "ERROR: No data in skill_signal_raw. Run arxiv_ingest.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if t1_period is None:
        t1_period = periods[-1]
    if t0_period is None:
        # Use the period immediately before t1, or t1 itself if only one available.
        idx = periods.index(t1_period) if t1_period in periods else len(periods) - 1
        t0_period = periods[idx - 1] if idx > 0 else t1_period

    print(f"Scoring: t0={t0_period}, t1={t1_period}, snapshot_date={snapshot_date}")

    labor_decay_map = load_labor_decay()
    exposure_map = load_automation_exposure()

    counts_t0, total_t0 = load_signal_raw(db_url, t0_period)
    counts_t1, total_t1 = load_signal_raw(db_url, t1_period)

    all_skill_ids = set(exposure_map.keys())
    scored_rows: list[dict] = []

    for sid in sorted(all_skill_ids):
        ct0 = counts_t0.get(sid, 0.0)
        ct1 = counts_t1.get(sid, 0.0)

        freq_t0 = ct0 / total_t0
        freq_t1 = ct1 / total_t1

        rv = research_velocity(freq_t0, freq_t1)
        ld, ld_note = labor_decay_map.get(sid, (0.0, "no BLS mapping"))
        exposure = exposure_map.get(sid, 0.5)

        v_mod = composite_velocity(rv, ld)
        v_fast = scenario_fast(v_mod, exposure)

        scored_rows.append(
            {
                "skill_id": sid,
                "research_velocity": round(rv, 6),
                "labor_decay": round(ld, 6),
                "labor_decay_source_note": ld_note,
                "automation_exposure": round(exposure, 4),
                "velocity_moderate": round(v_mod, 6),
                "velocity_fast": round(v_fast, 6),
                "direction_moderate": direction(v_mod),
                "direction_fast": direction(v_fast),
            }
        )

    write_snapshots(scored_rows, snapshot_date, db_url)
    rising_m = sum(1 for r in scored_rows if r["direction_moderate"] == "rising")
    declining_m = sum(1 for r in scored_rows if r["direction_moderate"] == "declining")
    print(
        f"Snapshot summary: {len(scored_rows)} skills, "
        f"{rising_m} rising, {declining_m} declining (moderate scenario)."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score skill trends and write a snapshot.")
    parser.add_argument("--snapshot-date", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--t0-period", default=None, help="ISO week t0, e.g. 2026-W41")
    parser.add_argument("--t1-period", default=None, help="ISO week t1, e.g. 2026-W42")
    args = parser.parse_args()

    sd = date.fromisoformat(args.snapshot_date) if args.snapshot_date else None
    main(snapshot_date=sd, t0_period=args.t0_period, t1_period=args.t1_period)
