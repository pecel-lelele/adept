"""Live job openings pipeline (owner M4): public job feeds → `job_postings` and the seed CSV.

    source        → employer career-site APIs (Greenhouse, Lever, Ashby, SmartRecruiters,
                    Workday, Jibe) and remote-job APIs (Himalayas, Jobicy, Remote OK, Remotive);
                    Careerjet / Jooble / web3.career when their keys are set (boards.py)
    preprocessing → Malaysia or Malaysia-eligible remote only; HTML → text; dedupe by
                    source + board + posting id; ad text is used in memory and never stored;
                    skills in >= 70% of one employer's ads are dropped as boilerplate
    features      → skills named in the ad (the CV parser's catalogue matcher), certifications
                    named by exam code, seniority from title and source level
    model/method  → role = ordered job-title patterns per Adept role, else unassigned (a
                    skills-only fallback was tried and dropped for poor precision)
    evaluation    → per-source counts, share assigned, skills per ad, the most common
                    unassigned title words (catalogue gaps); title-rule accuracy on a
                    hand-labelled set in tests/pipelines/jobs
    serving       → src/data/seed/jobs/job_postings.csv + certifications.csv + fetch_log.json;
                    with --db, upsert into PostgreSQL and close openings no longer listed

Run from the repo root:
    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.jobs.run            # fetch + seed CSV
    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.jobs.run --db       # ... and database
    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.jobs.run --cached   # re-classify only
    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.jobs.run --refilter-locations
        # offline: re-apply the current location rule to the seed CSV (no network)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Any

import httpx
import psycopg

from app.core import seed as seed_rows
from app.features.pathway.catalogue_sources import (
    BNM_SOURCE,
    SEED_USD_RATE,
    SEED_USD_RATE_DATE,
    fetch_fx,
)
from app.features.profile.cv_parser import extract_skills
from pipelines.jobs import boards
from pipelines.jobs.certifications import CERTS
from pipelines.jobs.classify import RoleReq, assign_role, cert_mentions, seniority
from pipelines.jobs.sources import (
    CONNECTORS,
    SOURCE_NAMES,
    Fetcher,
    IncompleteRead,
    MissingKey,
    RawPosting,
    in_malaysia,
)

ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = ROOT / "src" / "data" / "seed" / "jobs"
RAW_DIR = ROOT / "src" / "data" / "raw" / "jobs"
POSTINGS_CSV = SEED_DIR / "job_postings.csv"
CERTS_CSV = SEED_DIR / "certifications.csv"
FETCH_LOG = SEED_DIR / "fetch_log.json"
# An opening not seen for this long is closed even if its board could not be read.
STALE_AFTER = timedelta(days=14)

POSTING_FIELDS = (
    "id", "source", "board", "source_name", "employer", "title", "location", "work_mode",
    "remote_scope", "employment_type", "seniority", "url", "api_url", "posted_at", "expires_at",
    "salary_min", "salary_max", "salary_currency", "salary_period", "role_id", "role_method",
    "skill_ids", "cert_ids", "first_seen", "last_seen", "active",
)  # fmt: skip
CERT_FIELDS = (
    "id", "name", "issuer", "exam_code", "url", "fee_amount", "fee_currency", "fee_myr",
    "fee_note", "fee_source_url", "level", "skill_ids", "validity_note", "verified_at",
)  # fmt: skip


def requirements() -> dict[str, list[RoleReq]]:
    out: dict[str, list[RoleReq]] = defaultdict(list)
    for r in seed_rows.rows("taxonomy", "role_skills"):
        out[r["role_id"]].append(RoleReq(r["skill_id"], float(r["importance"] or 0)))
    return dict(out)


def fetch(
    only: set[str] | None,
    *,
    selected: Sequence[boards.Board] | None = None,
    fetcher: Fetcher | None = None,
    deadline: float | None = None,
) -> tuple[list[RawPosting], list[dict[str, Any]]]:
    """Read the boards. The in-app refresh passes `selected` (the boards to run), a bounded
    `fetcher` and a monotonic `deadline`; boards not reached by then are logged as skipped."""
    fetcher = fetcher or Fetcher()
    postings: dict[str, RawPosting] = {}
    log: list[dict[str, Any]] = []
    for b in selected if selected is not None else boards.ALL:
        if only and b.source not in only and b.board not in only:
            continue
        entry: dict[str, Any] = {"source": b.source, "board": b.board, "employer": b.employer}
        found: list[RawPosting] = []
        if deadline is not None and time.monotonic() >= deadline:
            log.append(entry | {"status": "skipped", "kept": 0, "detail": "time budget reached"})
            continue
        try:
            found.extend(CONNECTORS[b.source](fetcher, b))
            entry |= {"status": "ok", "kept": len(found)}
        except IncompleteRead as exc:
            entry |= {"status": "partial", "kept": len(found), "detail": type(exc).__name__}
        except MissingKey as exc:
            entry |= {"status": "skipped", "kept": 0, "detail": f"set {exc} to enable"}
        except PermissionError as exc:
            entry |= {"status": "blocked", "kept": 0, "detail": type(exc).__name__}
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            entry |= {"status": "error", "kept": 0, "detail": type(exc).__name__}
        for p in found:
            if p.title and p.url:
                postings.setdefault(f"{p.source}:{p.board}:{p.source_id}", p)
        print(f"  {b.source:16} {b.board:20} {entry['status']:8} {entry['kept']:4}", flush=True)
        log.append(entry)
    return list(postings.values()), log


# An employer's ads share boilerplate (company profile, AI-in-hiring notice, benefits). A skill
# named in at least this share of one employer board's ads is boilerplate, not a requirement.
BOILERPLATE_SHARE = 0.7
BOILERPLATE_MIN_ADS = 5


def boilerplate_skills(skill_sets: dict[str, list[set[str]]]) -> dict[str, set[str]]:
    """board -> skills that appear in nearly every one of that board's ads (pure)."""
    out: dict[str, set[str]] = {}
    for board, sets in skill_sets.items():
        if len(sets) < BOILERPLATE_MIN_ADS:
            continue
        counts = Counter(s for skills in sets for s in skills)
        out[board] = {s for s, n in counts.items() if n / len(sets) >= BOILERPLATE_SHARE}
    return out


def classify(raw: list[RawPosting], today: date) -> list[dict[str, Any]]:
    reqs = requirements()
    previous = {r["id"]: r for r in _read_csv(POSTINGS_CSV)}
    extracted = [{s.skill_id for s in extract_skills(p.text)} for p in raw]
    by_board: dict[str, list[set[str]]] = defaultdict(list)
    for p, skills_found in zip(raw, extracted, strict=True):
        if p.employer:  # employer career sites only; job boards mix many employers
            by_board[f"{p.source}:{p.board}"].append(skills_found)
    boiler = boilerplate_skills(by_board)
    rows: list[dict[str, Any]] = []
    for p, skills_found in zip(raw, extracted, strict=True):
        pid = f"{p.source}:{p.board}:{p.source_id}"[:300]
        skills = sorted(skills_found - boiler.get(f"{p.source}:{p.board}", set()))
        role_id, method = assign_role(p.title, reqs)
        rows.append(
            {
                "id": pid,
                "source": p.source,
                "board": p.board,
                "source_name": SOURCE_NAMES[p.source],
                "employer": p.employer or "Not stated",
                "title": p.title[:300],
                "location": (p.location or "")[:200],
                "work_mode": p.work_mode,
                "remote_scope": p.remote_scope,
                "employment_type": (p.employment_type or "")[:80],
                "seniority": seniority(p.title, p.experience_level),
                "url": p.url,
                "api_url": p.api_url,
                "posted_at": p.posted_at.isoformat() if p.posted_at else "",
                "expires_at": p.expires_at.isoformat() if p.expires_at else "",
                "salary_min": _num(p.salary_min),
                "salary_max": _num(p.salary_max),
                "salary_currency": p.salary_currency,
                "salary_period": p.salary_period,
                "role_id": role_id or "",
                "role_method": method,
                "skill_ids": "{" + ",".join(skills) + "}",
                "cert_ids": "{" + ",".join(cert_mentions(p.text)) + "}",
                "first_seen": previous.get(pid, {}).get("first_seen") or today.isoformat(),
                "last_seen": today.isoformat(),
                "active": "true",
            }
        )
    rows.sort(key=lambda r: (r["role_id"] or "~", r["employer"], r["title"], r["id"]))
    return rows


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Coverage numbers printed after every run and kept in fetch_log.json."""
    n = len(rows) or 1
    assigned = [r for r in rows if r["role_id"]]
    skill_counts = [r["skill_ids"].count(",") + 1 for r in rows if r["skill_ids"] != "{}"]
    report = {
        "openings": len(rows),
        "employers": len({r["employer"] for r in rows}),
        "by_source": dict(Counter(r["source"] for r in rows)),
        "assigned_share": round(len(assigned) / n, 3),
        "method": dict(Counter(r["role_method"] or "unassigned" for r in rows)),
        "by_role": dict(Counter(r["role_id"] for r in assigned).most_common()),
        "with_skills_share": round(len(skill_counts) / n, 3),
        "median_skills_per_ad": median(skill_counts) if skill_counts else 0,
        "with_cert_share": round(sum(r["cert_ids"] != "{}" for r in rows) / n, 3),
        "unassigned_families": unassigned_families(rows),
    }
    print(json.dumps(report, indent=2))
    return report


# Rough job families, used only to report which openings the role catalogue does not cover.
FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(rx, re.I))
    for name, rx in (
        (
            "software engineering",
            r"software|developer|backend|front ?end|full ?stack|development engineer|"
            r"engineer.*(java|go|rust|react|ios|android)|\bqa\b|quality assurance",
        ),
        (
            "finance & accounting",
            r"financ|account|audit|tax|treasury|\bfp&a\b|payroll|controller|deals|transaction",
        ),
        (
            "sales & business development",
            r"sales|business development|account executive|pre-sales|merchant|partnership|channel",
        ),
        ("operations & admin", r"operations|admin|coordinator|assistant|operator|executive"),
        ("engineering & technicians", r"engineer|technician"),
        ("people & HR", r"\bhr\b|people|talent|recruit"),
    )
)


def unassigned_families(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for r in rows:
        if r["role_id"]:
            continue
        name = next((n for n, rx in FAMILIES if rx.search(r["title"])), "other")
        out[name] += 1
    return dict(out.most_common())


def cert_rows() -> tuple[list[dict[str, Any]], str]:
    try:
        rate, on = fetch_fx("USD")
        fx = f"{BNM_SOURCE}, selling rate {rate:g} on {on.isoformat()}"
    except Exception as exc:  # noqa: BLE001 - network: fall back to the dated seed reading
        print(f"BNM rate unavailable ({exc}); using the seed rate", file=sys.stderr)
        rate, on = SEED_USD_RATE, SEED_USD_RATE_DATE
        fx = f"{BNM_SOURCE}, selling rate {rate:g} on {on.isoformat()} (seed reading)"
    rows = []
    for c in CERTS:
        myr = round(c.fee_amount * rate, 2) if c.fee_currency == "USD" else c.fee_amount
        rows.append(
            {
                "id": c.id,
                "name": c.name,
                "issuer": c.issuer,
                "exam_code": c.exam_code,
                "url": c.url,
                "fee_amount": f"{c.fee_amount:g}",
                "fee_currency": c.fee_currency,
                "fee_myr": f"{myr:.2f}",
                "fee_note": (
                    f"{c.fee_detail} Listed as {c.fee_currency} {c.fee_amount:g}; "
                    f"RM {myr:,.2f} at the Bank Negara Malaysia selling rate of {rate:g} "
                    f"on {on.isoformat()}."
                ).strip(),
                "fee_source_url": c.fee_source_url,
                "level": c.level,
                "skill_ids": "{" + ",".join(c.skill_ids) + "}",
                "validity_note": c.validity_note,
                "verified_at": c.verified_at.isoformat(),
            }
        )
    return rows, fx


def _num(v: Any) -> str:
    try:
        return f"{float(v):g}" if v not in (None, "", 0) else ""
    except (TypeError, ValueError):
        return ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def merge_postings(
    previous: list[dict[str, Any]],
    refreshed: list[dict[str, Any]],
    log: list[dict[str, Any]],
    today: date,
) -> list[dict[str, Any]]:
    """CSV and database use the same complete-read, expiry and stale closing rules."""
    complete = {(entry["source"], entry["board"]) for entry in log if entry["status"] == "ok"}
    seen = {row["id"] for row in refreshed}
    merged = {row["id"]: dict(row) for row in previous}
    merged.update({row["id"]: dict(row) for row in refreshed})
    for row in merged.values():
        missing = (row["source"], row["board"]) in complete and row["id"] not in seen
        stale = date.fromisoformat(row["last_seen"]) < today - STALE_AFTER
        expired = bool(row.get("expires_at") and date.fromisoformat(row["expires_at"]) < today)
        if missing or stale or expired:
            row["active"] = "false"
    return sorted(merged.values(), key=lambda row: row["id"])


def save_raw(raw: list[RawPosting], today: date) -> Path:
    """Full ads (with text) for re-classifying without refetching. Gitignored, never served."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{today.isoformat()}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for p in raw:
            fh.write(json.dumps(asdict(p), default=str, ensure_ascii=False) + "\n")
    return path


def load_raw(today: date | None) -> tuple[list[RawPosting], date]:
    files = sorted(RAW_DIR.glob("*.jsonl"))
    if today is not None:
        files = [f for f in files if f.stem == today.isoformat()]
    if not files:
        raise SystemExit(f"No cached fetch in {RAW_DIR}; run without --cached first.")
    path = files[-1]
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        for k in ("posted_at", "expires_at"):
            d[k] = date.fromisoformat(d[k]) if d.get(k) else None
        out.append(RawPosting(**d))
    return out, date.fromisoformat(path.stem)


def to_db(
    rows: list[dict[str, Any]],
    certs: list[dict[str, Any]],
    log: list[dict[str, Any]],
    today: date,
    url: str | None = None,
    conn: psycopg.Connection[tuple[Any, ...]] | None = None,
) -> int:
    """Upsert in one transaction (all or nothing); returns the active openings afterwards."""
    url = url or os.environ.get("DATABASE_URL", "postgresql://adept:adept@127.0.0.1:5433/adept")
    ok_boards = {(e["source"], e["board"]) for e in log if e["status"] == "ok"}
    with nullcontext(conn) if conn is not None else psycopg.connect(url) as conn:
        roles = {r[0] for r in conn.execute("SELECT id FROM roles").fetchall()}
        cols = ", ".join(CERT_FIELDS)
        marks = ", ".join(["%s"] * len(CERT_FIELDS))
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in CERT_FIELDS if c != "id")
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO certifications ({cols}) VALUES ({marks}) "
                f"ON CONFLICT (id) DO UPDATE SET {updates}",
                [[c[f] or None for f in CERT_FIELDS] for c in certs],
            )
        cols = ", ".join(POSTING_FIELDS)
        marks = ", ".join(["%s"] * len(POSTING_FIELDS))
        updates = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in POSTING_FIELDS if c not in ("id", "first_seen")
        )
        values = []
        for r in rows:
            r = dict(r)
            if r["role_id"] and r["role_id"] not in roles:
                r["role_id"], r["role_method"] = "", ""
            values.append([r[f] if r[f] != "" else None for f in POSTING_FIELDS])
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO job_postings ({cols}) VALUES ({marks}) "
                f"ON CONFLICT (id) DO UPDATE SET {updates}",
                values,
            )
        seen = [r["id"] for r in rows]
        for source, board in ok_boards:
            conn.execute(
                "UPDATE job_postings SET active = false WHERE source = %s AND board = %s "
                "AND active AND NOT (id = ANY(%s))",
                (source, board, seen),
            )
        conn.execute(
            "UPDATE job_postings SET active = false WHERE active AND "
            "(last_seen < %s OR (expires_at IS NOT NULL AND expires_at < %s))",
            (today - STALE_AFTER, today),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO job_fetch_log (source, board, fetched_on, status, kept, detail) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (source, board, fetched_on) "
                "DO UPDATE SET status = EXCLUDED.status, kept = EXCLUDED.kept, "
                "detail = EXCLUDED.detail",
                [
                    (e["source"], e["board"], today, e["status"], e["kept"], e.get("detail", ""))
                    for e in log
                ],
            )
        active = conn.execute("SELECT count(*) FROM job_postings WHERE active").fetchone()
    count = int(active[0]) if active else 0  # type: ignore[call-overload]
    print(f"database: {len(rows)} upserted, {count} active")
    return count


def keeps_location(row: dict[str, Any]) -> bool:
    """The fetch-time rule, applied to a stored row: Malaysian location, or a remote opening
    with a Malaysia-eligible scope (remote boards set the scope from their own region field)."""
    if row.get("work_mode") == "remote" and row.get("remote_scope"):
        return True
    return in_malaysia(row.get("location"))


def refilter_locations(
    rows: list[dict[str, Any]], log: dict[str, Any], applied_on: date
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Drop stored openings the current location rule rejects; keep counts consistent.

    Pure: returns the kept rows and an updated fetch log (evaluation recomputed on the kept
    active rows; per-board `kept` reduced by rows dropped from that board's latest fetch).
    `fetched_on` is unchanged because no source was read again.
    """
    kept = [r for r in rows if keeps_location(r)]
    dropped = [r for r in rows if not keeps_location(r)]
    fetched_on = log.get("fetched_on")
    from_last_fetch = Counter(
        (r["source"], r["board"]) for r in dropped if r.get("last_seen") == fetched_on
    )
    boards_log = []
    for entry in log.get("boards", []):
        entry = dict(entry)
        cut = from_last_fetch.get((entry.get("source"), entry.get("board")), 0)
        if cut and isinstance(entry.get("kept"), int):
            entry["kept"] = max(0, entry["kept"] - cut)
        boards_log.append(entry)
    updated = {
        **log,
        "evaluation": evaluate([r for r in kept if r.get("active") == "true"]),
        "boards": boards_log,
        "location_refilter": {
            "applied_on": applied_on.isoformat(),
            "rule": (
                "primary location in Malaysia (a bare Remote/Anywhere counts as missing), or a "
                "remote opening with a Malaysia-eligible scope"
            ),
            "dropped": len(dropped),
            "dropped_by_source": dict(Counter(r["source"] for r in dropped).most_common()),
            "network": False,
        },
    }
    return kept, updated


def refilter_seed(applied_on: date) -> int:
    rows = _read_csv(POSTINGS_CSV)
    log = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.exists() else {}
    kept, updated = refilter_locations(rows, log, applied_on)
    _write_csv(POSTINGS_CSV, POSTING_FIELDS, kept)
    FETCH_LOG.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"kept {len(kept)} of {len(rows)} openings; dropped {len(rows) - len(kept)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", action="store_true", help="also upsert into DATABASE_URL")
    ap.add_argument("--cached", action="store_true", help="re-classify the latest raw fetch")
    ap.add_argument("--only", nargs="*", help="limit to these sources or boards")
    ap.add_argument(
        "--refilter-locations",
        action="store_true",
        help="offline: drop seed rows the current location rule rejects",
    )
    args = ap.parse_args()
    if args.refilter_locations:
        return refilter_seed(date.today())

    if args.cached:
        raw, today = load_raw(None)
        previous = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.exists() else {}
        log = previous.get("boards", [])
    else:
        today = date.today()
        print(f"fetching {len(boards.ALL)} boards ...")
        raw, log = fetch(set(args.only) if args.only else None)
        print(f"raw ads cached at {save_raw(raw, today).relative_to(ROOT)}")

    refreshed = classify(raw, today)
    rows = merge_postings(_read_csv(POSTINGS_CSV), refreshed, log, today)
    report = evaluate([row for row in rows if row["active"] == "true"])
    certs, fx = cert_rows()
    _write_csv(POSTINGS_CSV, POSTING_FIELDS, rows)
    _write_csv(CERTS_CSV, CERT_FIELDS, certs)
    FETCH_LOG.write_text(
        json.dumps(
            {"fetched_on": today.isoformat(), "fx": fx, "evaluation": report, "boards": log},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {POSTINGS_CSV.relative_to(ROOT)} ({len(rows)} openings), {CERTS_CSV.name}")
    if args.db:
        to_db(refreshed, certs, log, today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
