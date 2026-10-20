"""Live course catalogue sync (F5): live sources → PostgreSQL `courses`.

- Microsoft Learn: titles, URLs and durations are refreshed from the Catalog API; a curated
  item the API no longer lists is flagged `retired_at` (kept for progress history, never
  recommended again).
- Coursera: each curated course is checked against Coursera's public catalog API; a 404
  retires it, a network failure leaves it as it was.
- HRD Corp provider rows: re-written from their hand-checked definitions.
- Foreign-currency prices (e.g. Coursera Plus in USD) are re-priced in ringgit at the live
  Bank Negara Malaysia selling rate, stored in `fx_rates`.

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
from app.core.logging import get_logger
from app.features.guardrails.datasync import SyncResult, run_logged
from app.features.pathway import catalogue_sources as src

log = get_logger("app.pathway.sync")

SOURCE = "Course catalogue (Microsoft Learn API, Coursera, HRD Corp providers)"

_UPSERT_SQL = """
INSERT INTO courses (id, title, provider, url, hours, cost_myr, hrd_claimable, verified_at,
    skill_ids, level, source_name, source_url, hrd_note, language, duration_note, provider_ref,
    format, audience, price_basis, currency, list_price, provider_type, location, price_note,
    last_synced_at, retired_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, now(), NULL)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title, provider = EXCLUDED.provider, url = EXCLUDED.url,
    hours = EXCLUDED.hours, cost_myr = EXCLUDED.cost_myr,
    hrd_claimable = EXCLUDED.hrd_claimable, verified_at = EXCLUDED.verified_at,
    skill_ids = EXCLUDED.skill_ids, level = EXCLUDED.level,
    source_name = EXCLUDED.source_name, source_url = EXCLUDED.source_url,
    hrd_note = EXCLUDED.hrd_note, language = EXCLUDED.language,
    duration_note = EXCLUDED.duration_note, provider_ref = EXCLUDED.provider_ref,
    format = EXCLUDED.format, audience = EXCLUDED.audience,
    price_basis = EXCLUDED.price_basis, currency = EXCLUDED.currency,
    list_price = EXCLUDED.list_price, provider_type = EXCLUDED.provider_type,
    location = EXCLUDED.location, price_note = EXCLUDED.price_note,
    last_synced_at = now(){retired}
"""
# Confirmed available: clear any earlier retirement.
_UPSERT = _UPSERT_SQL.format(retired=", retired_at = NULL")
# Provider could not be checked: refresh the facts but keep whatever retirement state it had,
# so a failed check never brings a course the provider removed back into recommendations.
_UPSERT_KEEP_RETIRED = _UPSERT_SQL.format(retired="")
_RETIRE = "UPDATE courses SET retired_at = now() WHERE id = ANY(%s) AND retired_at IS NULL"


_FX = """
INSERT INTO fx_rates (currency, rate_date, selling_rate, source) VALUES (%s, %s, %s, %s)
ON CONFLICT (currency, rate_date) DO UPDATE SET selling_rate = EXCLUDED.selling_rate,
    fetched_at = now()
"""


def _job(
    payload: dict[str, Any],
    today: date,
    coursera_check: Callable[[str], bool | None],
    fx: tuple[float, date] | None,
) -> Callable[[psycopg.Connection[tuple[object, ...]]], SyncResult]:
    def job(conn: psycopg.Connection[tuple[object, ...]]) -> SyncResult:
        skills = {str(r[0]) for r in conn.execute("SELECT id FROM skills").fetchall()}
        rows = src.all_rows(payload, today, allow_missing=True)
        fx_detail = ""
        if fx is not None:
            rate, on = fx
            rows = src.with_fx(rows, rate, on)
            conn.execute(_FX, ("USD", on, rate, src.BNM_SOURCE))
            fx_detail = f"; USD at {rate:g} MYR ({on.isoformat()}, Bank Negara Malaysia)"
        src.validate(rows, skills)
        gone = [c.id for c in src.missing_curated(payload)]
        unknown: list[str] = []
        unknown_ids: set[str] = set()
        for row in src.COURSERA:
            status = coursera_check(row.provider_ref)
            if status is False:
                gone.append(row.id)
            elif status is None:
                unknown.append(row.provider_ref)
                unknown_ids.add(row.id)
        live = [r for r in rows if r.id not in gone]
        for r in live:
            conn.execute(
                _UPSERT_KEEP_RETIRED if r.id in unknown_ids else _UPSERT,
                (
                    r.id, r.title, r.provider, r.url, r.hours, r.cost_myr, r.hrd_claimable,
                    r.verified_at, list(r.skill_ids), r.level, r.source_name, r.source_url,
                    r.hrd_note, r.language, r.duration_note, r.provider_ref or None,
                    r.format, r.audience, r.price_basis, r.currency, r.list_price,
                    r.provider_type, r.location, r.price_note,
                ),
            )  # fmt: skip
        retired = conn.execute(_RETIRE, (gone,)).rowcount if gone else 0
        detail = f"{len(live)} courses refreshed{fx_detail}"
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
    fx: Callable[[], tuple[float, date] | None] | None = None,
) -> SyncReport:
    """`fx` returns (MYR per USD, date); by default the live Bank Negara Malaysia rate. If the
    rate is unavailable the seed rate stays, and its date shows how old it is."""

    def live_fx() -> tuple[float, date] | None:
        try:
            return src.fetch_fx("USD")
        except (OSError, ValueError, KeyError) as exc:
            log.warning("Bank Negara Malaysia rate unavailable, keeping the stored rate: %s", exc)
            return None

    def job(conn: psycopg.Connection[tuple[object, ...]]) -> SyncResult:
        data = payload if payload is not None else src.fetch_mslearn()
        rate = (fx or live_fx)()
        return _job(data, today or date.today(), coursera_check, rate)(conn)

    return run_logged(SOURCE, job)


if __name__ == "__main__":
    report = sync_catalogue()
    print(report.model_dump_json(indent=2))
    raise SystemExit(0 if report.status == "ok" else 1)
