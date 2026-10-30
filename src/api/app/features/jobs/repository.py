"""Job openings and certifications: PostgreSQL when M3_BACKEND=postgres, else the seed CSVs
written by src/pipelines/jobs (same rows `make seed` loads)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

from app.core import refdata, seed
from app.core.seed import pg_array

FETCH_LOG = seed.SEED_DIR / "jobs" / "fetch_log.json"
FRESH_DAYS = 14  # an ad not re-seen within this many days may have closed (M4-087)


@dataclass(frozen=True)
class Posting:
    id: str
    source: str
    board: str
    source_name: str
    employer: str
    title: str
    location: str
    work_mode: str
    remote_scope: str
    employment_type: str
    seniority: str
    url: str
    api_url: str
    posted_at: date | None
    first_seen: date
    last_seen: date
    role_id: str
    role_method: str
    skill_ids: tuple[str, ...]
    cert_ids: tuple[str, ...]
    # Not re-seen by a source read within FRESH_DAYS: shown only with a staleness label.
    stale: bool = False


@dataclass(frozen=True)
class CertRow:
    id: str
    name: str
    issuer: str
    exam_code: str
    url: str
    level: str
    fee_amount: float
    fee_currency: str
    fee_myr: float
    fee_note: str
    fee_source_url: str
    verified_at: date
    validity_note: str
    skill_ids: tuple[str, ...]


def _day(value: str) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def openings(*, include_stale: bool = False) -> list[Posting]:
    """Active openings, newest listing first. Expired ones are excluded even before the next
    pipeline run closes them. Ads not re-seen within FRESH_DAYS are excluded from counts and
    matching; ``include_stale`` returns them too, flagged ``stale`` so listings can label
    them instead of letting them silently vanish."""
    from pipelines.jobs.sources import in_malaysia

    today = date.today()
    out: list[Posting] = []
    for r in refdata.rows("jobs", "job_postings", active_only=True):
        if r.get("active", "true") != "true":
            continue
        # Apply the automatic publisher's own-location rule to older stored exports too.
        if not in_malaysia(r.get("location", "")):
            continue
        expires = _day(r.get("expires_at", ""))
        if expires and expires < today:
            continue
        first = _day(r["first_seen"]) or today
        last = _day(r["last_seen"]) or first
        stale = last < today - timedelta(days=FRESH_DAYS)
        if stale and not include_stale:
            continue
        out.append(
            Posting(
                id=r["id"],
                source=r["source"],
                board=r["board"],
                source_name=r["source_name"],
                employer=r["employer"],
                title=r["title"],
                location=r.get("location", ""),
                work_mode=r.get("work_mode") or "onsite",
                remote_scope=r.get("remote_scope", ""),
                employment_type=r.get("employment_type", ""),
                seniority=r.get("seniority") or "unknown",
                url=r["url"],
                api_url=r["api_url"],
                posted_at=_day(r.get("posted_at", "")),
                first_seen=first,
                last_seen=last,
                role_id=r.get("role_id", ""),
                role_method=r.get("role_method", ""),
                skill_ids=tuple(pg_array(r.get("skill_ids") or "{}")),
                cert_ids=tuple(pg_array(r.get("cert_ids") or "{}")),
                stale=stale,
            )
        )
    # Fresh ads first (newest listing first), then stale ones.
    out.sort(key=lambda p: (not p.stale, p.posted_at or p.first_seen, p.id), reverse=True)
    return out


def certifications() -> list[CertRow]:
    return [
        CertRow(
            id=r["id"],
            name=r["name"],
            issuer=r["issuer"],
            exam_code=r["exam_code"],
            url=r["url"],
            level=r["level"],
            fee_amount=float(r["fee_amount"]),
            fee_currency=r["fee_currency"],
            fee_myr=float(r["fee_myr"]),
            fee_note=r["fee_note"],
            fee_source_url=r["fee_source_url"],
            verified_at=date.fromisoformat(r["verified_at"][:10]),
            validity_note=r.get("validity_note", ""),
            skill_ids=tuple(pg_array(r["skill_ids"])),
        )
        for r in refdata.rows("jobs", "certifications")
    ]


def fetch_log() -> dict[str, object]:
    """The last pipeline run's summary (boards read, skipped or blocked), if present."""
    try:
        return dict(json.loads(FETCH_LOG.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def observation_date() -> date | None:
    """Last actual posting observation, including expired rows; never a request date."""
    dates = [
        day
        for row in refdata.rows("jobs", "job_postings")
        if (day := _day(row.get("last_seen", ""))) is not None
    ]
    return max(dates, default=None)
