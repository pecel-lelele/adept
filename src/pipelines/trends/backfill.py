"""One-time operator backfill for the trend paper store, and its portable seed (M1-024, M1-027).

Never called by the API or a page. Commands, in order:

  estimate     Print the plan, cost inputs and resolved target. No network, no model, no write.
  equivalence  Compare Gemini against MiniLM on the same papers and record the result. A pass
               stores the threshold; a failure means the switch does not happen.
  run          Fetch, match and commit every missing day from START_DAY in resumable chunks,
               then publish the rolling snapshot. Refuses to start without a passing report.
  export-seed  Check the measured store and write a portable seed to
               src/data/seed/trends/paper_store/ for later migration. Refuses an empty store.

Every command that writes needs `--target host:port/database`, matching the resolved database,
so nothing ever writes through an ambient connection by accident.

Stages: arXiv cs.AI submissions (public metadata, newest 50 per day) -> title + abstract ->
Gemini embeddings at 384 dimensions -> cosine >= one stored threshold per model -> equivalence
against MiniLM on the same papers (bar below) -> per-paper rows counted by the rolling series.

Run from the repository root:
  PYTHONPATH=src/api:src python -m pipelines.trends.backfill estimate
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.core import refdata
from app.core.config import get_settings
from app.core.db import connection
from app.features.data_refresh import (
    automatic_trends,
    repository,
    service,
    trend_fallback,
    trend_store,
)
from pipelines.trends import arxiv_ingest, score
from pipelines.trends.encoder import MODEL_ID, get_encoder

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed" / "trends" / "paper_store"
REPORT = trend_store.EQUIVALENCE_REPORT

# The pass bar, fixed before any live comparison was run. Spearman is over per-skill mention
# counts across the whole sample; the label share is over all catalogue skills on the radar's
# two 7-day windows, under both scenarios. Tuning these after a run would void the test.
MIN_SPEARMAN = 0.60
MIN_LABEL_AGREEMENT = 0.70
MIN_PAPERS = 500
# At least one full day's sample in each recent 7-day window must actually be compared.
MIN_RECENT_WINDOW_PAPERS = 50
DEFAULT_EQUIVALENCE_DAYS = 28

# An assumed list price for the printed estimate only; check it before relying on the figure.
GEMINI_USD_PER_MILLION_TOKENS = 0.15
TOKENS_PER_PAPER = 350
BACKFILL_BUDGET_S = 6 * 3600.0
RETRY_WAIT_S = 60.0
MAX_CONSECUTIVE_FAILURES = 5
RETRYABLE = (httpx.HTTPError, service.RefreshFailed, trend_fallback.FallbackUnavailable, OSError)


# ---------------------------------------------------------------------------
# Pure evaluation
# ---------------------------------------------------------------------------


def average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks with ties sharing their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Spearman rank correlation; 0 when either side has no variation."""
    if len(a) != len(b):
        raise ValueError("Spearman needs equal-length inputs")
    if len(a) < 2:
        return 0.0
    ra, rb = average_ranks(a), average_ranks(b)
    mean_a, mean_b = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(ra, rb, strict=True))
    var_a = sum((x - mean_a) ** 2 for x in ra)
    var_b = sum((y - mean_b) ** 2 for y in rb)
    return cov / (var_a * var_b) ** 0.5 if var_a > 0 and var_b > 0 else 0.0


Counts = Mapping[str, int]


def labels(
    before: Counts,
    total_before: int,
    after: Counts,
    total_after: int,
    skill_ids: Sequence[str],
    decay: Mapping[str, tuple[float, str]],
    exposure: Mapping[str, float],
) -> dict[str, tuple[str, str]]:
    """Per skill, the radar's (moderate, fast) label from the production scorer."""
    rows = score.score_rows(
        {k: float(v) for k, v in before.items()},
        total_before,
        {k: float(v) for k, v in after.items()},
        total_after,
        dict(decay),
        dict(exposure),
        skill_ids=set(skill_ids),
    )
    return {r["skill_id"]: (r["direction_moderate"], r["direction_fast"]) for r in rows}


def label_agreement(
    a: Mapping[str, tuple[str, str]], b: Mapping[str, tuple[str, str]], scenario: int
) -> float:
    """Share of skills keeping the same label; scenario 0 is moderate, 1 is fast."""
    return sum(a[s][scenario] == b[s][scenario] for s in a) / len(a) if a else 0.0


def verdict(
    rho: float,
    moderate: float,
    fast: float,
    papers: int,
    before_papers: int,
    after_papers: int,
) -> bool:
    return (
        papers >= MIN_PAPERS
        and before_papers >= MIN_RECENT_WINDOW_PAPERS
        and after_papers >= MIN_RECENT_WINDOW_PAPERS
        and rho >= MIN_SPEARMAN
        and moderate >= MIN_LABEL_AGREEMENT
        and fast >= MIN_LABEL_AGREEMENT
    )


def estimate(days: int, per_day: int = automatic_trends.PER_DAY) -> dict[str, float]:
    """Backfill upper bound from the sampling limits."""
    papers = days * per_day
    tokens = papers * TOKENS_PER_PAPER
    return {
        "days": days,
        "papers": papers,
        "arxiv_minutes": round(days * automatic_trends.ARXIV_SPACING_S / 60, 1),
        "gemini_batches": papers // trend_fallback.BATCH + 1,
        "gemini_million_tokens": round(tokens / 1e6, 2),
        "gemini_usd_estimate": round(tokens / 1e6 * GEMINI_USD_PER_MILLION_TOKENS, 2),
    }


# ---------------------------------------------------------------------------
# Target safety
# ---------------------------------------------------------------------------


def resolved_target() -> str:
    """`host:port/database` with no credentials."""
    parts = urlsplit(get_settings().database_url)
    return f"{parts.hostname}:{parts.port or 5432}{parts.path}"


def require_target(given: str | None) -> None:
    if given != resolved_target():
        raise SystemExit(f"Refusing to write: pass --target {resolved_target()} to confirm it.")


def _skills() -> list[tuple[str, str]]:
    return [(r["id"], r["label"]) for r in refdata.rows("taxonomy", "skills")]


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sample:
    days: dict[date, list[dict[str, str]]]  # common comparison papers
    minilm: dict[str, list[str]]
    fetched_days: dict[date, list[dict[str, str]]]  # complete days for Gemini storage


def _stored_minilm(start: date, end: date) -> dict[str, list[str]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT arxiv_id, skills FROM trend_paper_mentions "
            "WHERE method = %s AND published_on BETWEEN %s AND %s",
            (trend_store.MINILM_METHOD, start, end),
        ).fetchall()
    return {r["arxiv_id"]: list(r["skills"]) for r in rows}


def load_sample(start: date, end: date, stop: threading.Event, today: date) -> Sample:
    """The same papers under both models: stored MiniLM rows if any, else MiniLM runs now."""
    span = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    fetched = automatic_trends.fetch_days(span, time.monotonic() + BACKFILL_BUDGET_S, stop)
    stored = _stored_minilm(start, end)
    if stored:
        kept = {
            day: [p for p in papers if p["arxiv_id"] in stored] for day, papers in fetched.items()
        }
        print(f"MiniLM evidence: {len(stored)} stored M1-014 rows.")
        return Sample(kept, stored, fetched)
    papers = [p for day in fetched.values() for p in day]
    print(f"MiniLM evidence: none stored; encoding {len(papers)} papers now.")
    encoder = get_encoder()
    skills = _skills()
    ids = [sid for sid, _label in skills]
    vectors = dict(
        zip(ids, encoder.encode([label for _s, label in skills], batch_size=64), strict=True)
    )
    found = arxiv_ingest.paper_mentions(papers, ids, vectors, encoder)
    minilm = {p["arxiv_id"]: f for p, f in zip(papers, found, strict=True)}
    with repository.write_connection(time.monotonic() + 300) as conn:
        trend_store.save_days(conn, fetched, minilm, trend_store.MINILM_METHOD, MODEL_ID, today)
    return Sample(fetched, minilm, fetched)


def _counts(
    days: Mapping[date, list[dict[str, str]]],
    mentions: Mapping[str, list[str]],
    start: date,
    end: date,
    ids: Sequence[str],
) -> tuple[dict[str, int], int]:
    counts = dict.fromkeys(ids, 0)
    total = 0
    for day, papers in days.items():
        if start <= day <= end:
            total += len(papers)
            for paper in papers:
                for sid in mentions.get(paper["arxiv_id"], []):
                    if sid in counts:
                        counts[sid] += 1
    return counts, total


def compare(
    sample: Sample,
    gemini: Mapping[str, list[str]],
    threshold: float,
    rate: float,
    start: date,
    end: date,
    today: date,
) -> dict[str, object]:
    """The report for one sample; uses the production scorer for labels."""
    ids = [sid for sid, _label in _skills()]
    a, papers = _counts(sample.days, sample.minilm, start, end, ids)
    b, _ = _counts(sample.days, gemini, start, end, ids)
    rho = spearman([a[s] for s in ids], [b[s] for s in ids])
    mid = end - timedelta(days=automatic_trends.WINDOW_DAYS)
    first = mid - timedelta(days=automatic_trends.WINDOW_DAYS - 1)
    decay, exposure = score.load_labor_decay(), score.load_automation_exposure()
    window_after = (mid + timedelta(days=1), end)
    before_counts, before_papers = _counts(sample.days, sample.minilm, first, mid, ids)
    after_counts, after_papers = _counts(sample.days, sample.minilm, *window_after, ids)
    side_a = labels(before_counts, before_papers, after_counts, after_papers, ids, decay, exposure)
    side_b = labels(
        *_counts(sample.days, gemini, first, mid, ids),
        *_counts(sample.days, gemini, *window_after, ids),
        ids,
        decay,
        exposure,
    )
    moderate = label_agreement(side_a, side_b, 0)
    fast = label_agreement(side_a, side_b, 1)
    measured = {s for s in ids if a[s] or b[s]}
    return {
        "model": trend_fallback.model_label(),
        "reference_model": MODEL_ID,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "evaluated_on": today.isoformat(),
        "papers": papers,
        "recent_window_papers": {"before": before_papers, "after": after_papers},
        "threshold": threshold,
        "rule": trend_fallback.RULE_MINILM,
        "reference_rate": rate,
        "spearman": round(rho, 4),
        "label_agreement_moderate": round(moderate, 4),
        "label_agreement_fast": round(fast, 4),
        # A diagnostic only: skills neither model mentioned agree trivially.
        "label_agreement_moderate_mentioned_skills": round(
            label_agreement({s: side_a[s] for s in measured}, {s: side_b[s] for s in measured}, 0),
            4,
        ),
        "mentioned_skills": len(measured),
        "pass_bar": {
            "min_papers": MIN_PAPERS,
            "min_papers_per_recent_window": MIN_RECENT_WINDOW_PAPERS,
            "min_spearman": MIN_SPEARMAN,
            "min_label_agreement_each_scenario": MIN_LABEL_AGREEMENT,
        },
        "passed": verdict(rho, moderate, fast, papers, before_papers, after_papers),
    }


def run_equivalence(days: int) -> int:
    if not trend_fallback.enabled():
        raise SystemExit("Set EMBEDDINGS_PROVIDER=gemini and GEMINI_API_KEY for this process.")
    today = datetime.now(UTC).date()
    end = today - timedelta(days=automatic_trends.SETTLE_DAYS)
    start = end - timedelta(days=days - 1)
    stop = threading.Event()
    sample = load_sample(start, end, stop, today)
    papers = [p for day in sample.days.values() for p in day]
    if not papers:
        print("No papers to compare; the switch does not happen.", file=sys.stderr)
        return 1
    mentions_total = sum(len(sample.minilm.get(p["arxiv_id"], [])) for p in papers)
    rate = mentions_total / len(papers)
    # Compare only papers with MiniLM evidence, but match and save every fetched paper.
    # Replacing a Gemini day with the intersection would shrink its denominator.
    fetched = [p for day in sample.fetched_days.values() for p in day]
    sims = automatic_trends.gemini_similarities(
        fetched, _skills(), time.monotonic() + BACKFILL_BUDGET_S, stop, patient=True
    )
    by_id = {p["arxiv_id"]: row for p, row in zip(fetched, sims, strict=True)}
    model = trend_fallback.model_label()
    threshold = trend_store.calibration(model)
    if threshold is None:
        threshold = trend_fallback.calibrated_threshold(
            [by_id[p["arxiv_id"]] for p in papers], rate
        )
    found = trend_fallback.mentions(sims, threshold)
    gemini = {p["arxiv_id"]: f for p, f in zip(fetched, found, strict=True)}
    report = compare(sample, gemini, threshold, rate, start, end, today)
    if report["passed"]:
        with repository.write_connection(time.monotonic() + 300) as conn:
            trend_store.save_calibration(
                conn, model, threshold, trend_fallback.RULE_MINILM, rate, len(papers), today
            )
            row = conn.execute(
                "SELECT threshold FROM trend_matcher_calibration WHERE model = %s", (model,)
            ).fetchone()
            if row is None or float(row[0]) != threshold:
                # A concurrent equivalence run stored a different threshold. Retry against it;
                # never label rows scored with one threshold as using another.
                raise SystemExit(
                    "Stored calibration changed; rerun equivalence before saving days."
                )
            trend_store.save_days(
                conn, sample.fetched_days, gemini, trend_store.GEMINI_METHOD, model, today
            )
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        print("Equivalence FAILED: the series stays on MiniLM.", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# Backfill and seed
# ---------------------------------------------------------------------------


def passing_report(model: str) -> bool:
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return report.get("passed") is True and report.get("model") == model


def run_backfill() -> int:
    if trend_store.series_method() != trend_store.GEMINI_METHOD:
        raise SystemExit(
            f"The backfill is for the Gemini series; it needs a passing report in {REPORT} "
            "and TRENDS_MATCHER other than minilm."
        )
    if not trend_fallback.enabled():
        raise SystemExit("Set EMBEDDINGS_PROVIDER=gemini and GEMINI_API_KEY for this process.")
    if not passing_report(trend_fallback.model_label()):
        raise SystemExit(f"No passing equivalence report for this model in {REPORT}.")
    stop = threading.Event()
    failures = 0
    today = datetime.now(UTC).date()
    while True:
        missing = automatic_trends.missing_days(trend_store.fetched_days(), today)
        if not missing:
            break
        print(f"{len(missing)} days left, resuming at {missing[0]}.", flush=True)
        try:
            stored, papers = automatic_trends.catch_up(
                missing, time.monotonic(), BACKFILL_BUDGET_S, stop, today, patient=True
            )
            failures = 0
            print(f"Committed {stored} days, {papers} papers.", flush=True)
        except RETRYABLE as exc:
            # Everything committed so far stays; provider text may hold secrets, so log the type.
            failures += 1
            print(f"Chunk failed ({type(exc).__name__}), attempt {failures}.", flush=True)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                print("Stopping; run again to resume.", file=sys.stderr)
                return 1
            time.sleep(RETRY_WAIT_S)
    stored_days = set(trend_store.fetched_days())
    outcome = automatic_trends.publish_rolling(
        stored_days, 0, time.monotonic(), BACKFILL_BUDGET_S, today
    )
    print(outcome.message)
    return 0


def validate_export(
    days: Sequence[Mapping[str, object]], papers: Sequence[Mapping[str, object]], method: str
) -> tuple[date, date]:
    """Refuse a header-only or internally inconsistent seed before touching existing files."""
    if not days or not papers:
        raise ValueError("No measured paper history to export; run the backfill first.")
    first = days[0]["day"]
    last = days[-1]["day"]
    if not isinstance(first, date) or not isinstance(last, date):
        raise ValueError("Stored paper days have invalid dates.")
    if first > last or len(days) != (last - first).days + 1:
        raise ValueError("Series has missing or out-of-order dates; export refused.")
    if last > datetime.now(UTC).date() - timedelta(days=automatic_trends.ARXIV_LAG_DAYS):
        raise ValueError("Series includes unannounced future dates; export refused.")
    counts = Counter(p["published_on"] for p in papers)
    stored_dates = {row["day"] for row in days}
    for index, row in enumerate(days):
        day = row["day"]
        if day != first + timedelta(days=index) or row["method"] != method:
            raise ValueError("Paper-store days are out of order or mix matching methods.")
        if counts[day] != row["papers"]:
            raise ValueError(f"Paper total differs from stored rows on {day}; export refused.")
    if any(p["method"] != method or p["published_on"] not in stored_dates for p in papers):
        raise ValueError("Paper-store records mix matching methods or dates.")
    return first, last


def export_seed() -> int:
    """Deterministic CSVs of the active series; public IDs and labels only, no abstract text."""
    method = trend_store.series_method()
    # One MVCC snapshot keeps the exported day denominators and paper rows together
    # even if a settled day is replaced while these three reads run.
    with connection() as conn, conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        days = conn.execute(
            "SELECT day, method, papers, fetched_on FROM trend_fetched_days "
            "WHERE method = %s ORDER BY day",
            (method,),
        ).fetchall()
        papers = conn.execute(
            "SELECT arxiv_id, published_on, method, model, skills FROM trend_paper_mentions "
            "WHERE method = %s ORDER BY published_on, arxiv_id",
            (method,),
        ).fetchall()
        calibrations = conn.execute(
            "SELECT model, threshold, rule, reference_rate, reference_papers, calibrated_on "
            "FROM trend_matcher_calibration ORDER BY model"
        ).fetchall()

    first, last = validate_export(days, papers, method)
    if method == trend_store.GEMINI_METHOD and not any(
        row["model"] == trend_fallback.model_label() for row in calibrations
    ):
        raise ValueError("Gemini calibration is missing; export refused.")
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"Validated {len(days)} measured days ({first}..{last}), "
        f"{len(papers)} papers, method {method}."
    )

    def write(name: str, header: list[str], rows: list[list[object]]) -> None:
        with (SEED_DIR / f"{name}.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        print(f"{name}.csv: {len(rows)} rows")

    write(
        "trend_fetched_days",
        ["day", "method", "papers", "fetched_on"],
        [[r["day"], r["method"], r["papers"], r["fetched_on"]] for r in days],
    )
    write(
        "trend_paper_mentions",
        ["arxiv_id", "published_on", "method", "model", "skills"],
        [
            [
                r["arxiv_id"],
                r["published_on"],
                r["method"],
                r["model"],
                "{" + ",".join(sorted(r["skills"])) + "}",
            ]
            for r in papers
        ],
    )
    write(
        "trend_matcher_calibration",
        ["model", "threshold", "rule", "reference_rate", "reference_papers", "calibrated_on"],
        [
            [
                r["model"],
                r["threshold"],
                r["rule"],
                r["reference_rate"],
                r["reference_papers"],
                r["calibrated_on"],
            ]
            for r in calibrations
        ],
    )
    return 0


def print_estimate() -> int:
    today = datetime.now(UTC).date()
    last = today - timedelta(days=automatic_trends.ARXIV_LAG_DAYS)
    days = (last - automatic_trends.START_DAY).days + 1
    print(f"Range: {automatic_trends.START_DAY}..{last}")
    print(json.dumps(estimate(days), indent=2))
    print(f"Target database: {resolved_target()}")
    settings = get_settings()
    print(f"Gemini key present: {bool(settings.gemini_api_key)}")
    print(f"Embeddings provider: {settings.embeddings_provider}")
    print(f"Series method: {trend_store.series_method()}")
    print(f"Pass bar: spearman >= {MIN_SPEARMAN}, labels >= {MIN_LABEL_AGREEMENT}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("estimate")
    equivalent = commands.add_parser("equivalence")
    equivalent.add_argument("--target")
    equivalent.add_argument("--days", type=int, default=DEFAULT_EQUIVALENCE_DAYS)
    backfill = commands.add_parser("run")
    backfill.add_argument("--target")
    exported = commands.add_parser("export-seed")
    exported.add_argument("--target")
    args = parser.parse_args(argv)
    if args.command == "estimate":
        return print_estimate()
    require_target(args.target)
    if args.command == "export-seed":
        return export_seed()
    return run_equivalence(args.days) if args.command == "equivalence" else run_backfill()


if __name__ == "__main__":
    raise SystemExit(main())
