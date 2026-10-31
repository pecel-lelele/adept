"""Job openings and certifications: PostgreSQL when M3_BACKEND=postgres, else the seed CSVs
written by src/pipelines/jobs (same rows `make seed` loads)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from app.core import refdata, seed
from app.core.config import get_settings
from app.core.seed import pg_array

FETCH_LOG = seed.SEED_DIR / "jobs" / "fetch_log.json"


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
    # Outside the configured observation window: shown only with a staleness label.
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


def _read_postings(keep: Callable[[dict[str, str]], bool], include_stale: bool) -> list[Posting]:
    """Stored rows that pass ``keep``, as postings. Expired ones are excluded even before the
    next pipeline run closes them. Ads outside JOBS_STALE_DAYS are excluded from counts and
    matching; ``include_stale`` returns them too, flagged ``stale`` so listings can label
    them instead of letting them silently vanish."""
    today = date.today()
    out: list[Posting] = []
    for r in refdata.rows("jobs", "job_postings", active_only=True):
        if r.get("active", "true") != "true":
            continue
        if not keep(r):
            continue
        expires = _day(r.get("expires_at", ""))
        if expires and expires < today:
            continue
        first = _day(r["first_seen"]) or today
        last = _day(r["last_seen"]) or first
        stale = last < today - timedelta(days=get_settings().jobs_stale_days)
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


def openings(*, include_stale: bool = False) -> list[Posting]:
    """Active openings, newest listing first, limited to postings whose own location is in
    Malaysia. See ``_read_postings`` for expiry and staleness."""
    from pipelines.jobs.sources import in_malaysia

    # Apply the automatic publisher's own-location rule to older stored exports too.
    return _read_postings(lambda r: in_malaysia(r.get("location", "")), include_stale)


def malaysia_relevant_openings(*, include_stale: bool = False) -> list[Posting]:
    """``openings`` plus remote ads open to Malaysia or to anyone: the job board and the role
    detail page only. Other surfaces keep the own-location rule."""
    from pipelines.jobs.sources import malaysia_relevance

    return _read_postings(
        lambda r: (
            malaysia_relevance(
                r.get("location", ""), r.get("work_mode") or "onsite", r.get("remote_scope", "")
            )
            != "not_malaysia"
        ),
        include_stale,
    )


def relevance(p: Posting) -> str:
    """The posting's Malaysia-relevance state (see pipelines.jobs.sources.malaysia_relevance)."""
    from pipelines.jobs.sources import malaysia_relevance

    return malaysia_relevance(p.location, p.work_mode, p.remote_scope)


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
