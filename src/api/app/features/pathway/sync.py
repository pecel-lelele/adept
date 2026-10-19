"""Live course catalogue sync (F5): live sources → PostgreSQL `courses`.

- Microsoft Learn: titles, URLs and durations are refreshed from the Catalog API; a curated
  item the API no longer lists is flagged `retired_at` (kept for progress history, never
  recommended again).
- Coursera: each curated course is checked against Coursera's public catalog API; a 404
  retires it, a network failure leaves it as it was.
- HRD Corp provider rows: re-written from their hand-checked definitions.

Run on a schedule (e.g. a Replit scheduled job) with:
    cd src/api && python -m app.features.pathway.sync
or trigger `POST /api/v1/pathway/catalogue/sync` with the `X-Sync-Token` header.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import psycopg

from app.contracts.guardrails import SyncReport
from app.features.guardrails.datasync import SyncResult, run_logged
from app.features.pathway import catalogue_sources as src

SOURCE = "Course catalogue (Microsoft Learn API, Coursera, HRD Corp providers)"

_UPSERT = """
INSERT INTO courses (id, title, provider, url, hours, cost_myr, hrd_claimable, verified_at,
    skill_ids, level, source_name, source_url, hrd_note, language, duration_note, provider_ref,
    last_synced_at, retired_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), NULL)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title, provider = EXCLUDED.provider, url = EXCLUDED.url,
    hours = EXCLUDED.hours, cost_myr = EXCLUDED.cost_myr,
    hrd_claimable = EXCLUDED.hrd_claimable, verified_at = EXCLUDED.verified_at,
    skill_ids = EXCLUDED.skill_ids, level = EXCLUDED.level,
    source_name = EXCLUDED.source_name, source_url = EXCLUDED.source_url,
    hrd_note = EXCLUDED.hrd_note, language = EXCLUDED.language,
    duration_note = EXCLUDED.duration_note, provider_ref = EXCLUDED.provider_ref,
    last_synced_at = now(), retired_at = NULL
"""
_RETIRE = "UPDATE courses SET retired_at = now() WHERE id = ANY(%s) AND retired_at IS NULL"


def _job(
    payload: dict[str, Any], today: date, coursera_check: Callable[[str], bool | None]
) -> Callable[[psycopg.Connection[tuple[object, ...]]], SyncResult]:
    def job(conn: psycopg.Connection[tuple[object, ...]]) -> SyncResult:
        skills = {str(r[0]) for r in conn.execute("SELECT id FROM skills").fetchall()}
        rows = src.all_rows(payload, today, allow_missing=True)
        src.validate(rows, skills)
        gone = [c.id for c in src.missing_curated(payload)]
        unknown: list[str] = []
        for row in src.COURSERA:
            status = coursera_check(row.provider_ref)
            if status is False:
                gone.append(row.id)
            elif status is None:
                unknown.append(row.provider_ref)
        live = [r for r in rows if r.id not in gone]
        for r in live:
            conn.execute(
                _UPSERT,
                (
                    r.id, r.title, r.provider, r.url, r.hours, r.cost_myr, r.hrd_claimable,
                    r.verified_at, list(r.skill_ids), r.level, r.source_name, r.source_url,
                    r.hrd_note, r.language, r.duration_note, r.provider_ref or None,
                ),
            )  # fmt: skip
        retired = conn.execute(_RETIRE, (gone,)).rowcount if gone else 0
        detail = f"{len(live)} courses refreshed"
        if gone:
            detail += f"; retired: {', '.join(sorted(gone))}"
        if unknown:
            detail += f"; Coursera unreachable for: {', '.join(unknown)}"
        return len(live), retired, detail

    return job


def sync_catalogue(
    payload: dict[str, Any] | None = None,
    today: date | None = None,
    coursera_check: Callable[[str], bool | None] = src.coursera_status,
) -> SyncReport:
    def job(conn: psycopg.Connection[tuple[object, ...]]) -> SyncResult:
        data = payload if payload is not None else src.fetch_mslearn()
        return _job(data, today or date.today(), coursera_check)(conn)

    return run_logged(SOURCE, job)


if __name__ == "__main__":
    report = sync_catalogue()
    print(report.model_dump_json(indent=2))
    raise SystemExit(0 if report.status == "ok" else 1)
