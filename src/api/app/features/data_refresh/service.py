"""Live data refresh (Core): fetch, validate, then upsert into the app's own DATABASE_URL.

GitHub runners cannot reach the deployment database, so scheduled workflows never write
production rows. An administrator runs the EXISTING pipeline functions in this API process:

- courses: Microsoft Learn Catalog API + Coursera + Bank Negara FX through
  `app.features.pathway.sync.sync_catalogue` (one transaction, rolled back on any failure).
- jobs: the keyless feeds plus the keyed boards whose key is configured, through
  `pipelines.jobs.run` (fetch, classify, `to_db` in one transaction).
- labour: DOSM monthly Labour Force Survey through `pipelines.trends.malaysia_context`.

Fail closed: a fetch error or a validation failure writes nothing and the last good rows stay
served. Every network call has a timeout and a size cap, destinations must be public https
hosts (also across redirects), the whole run has a time budget, and one run per source at a
time (in-process lock plus a PostgreSQL advisory lock for other API instances).

Freshness is read from stored data and the run log, never from the request date.
"""

from __future__ import annotations

import ipaddress
import json
import os
import secrets
import socket
import threading
import time
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

import httpx
import psycopg

from app.contracts.data_refresh import (
    DataFreshnessResponse,
    DataRefreshResult,
    DataSourceFreshness,
    DataSourceId,
    RefreshableSource,
)
from app.core import refdata, seed
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.features.data_refresh import repository

log = get_logger("app.data_refresh")

REFRESHABLE: tuple[RefreshableSource, ...] = ("courses", "jobs", "labour", "trends")
USER_AGENT = "adept-data-refresh/1.0"
MAX_BYTES = 40_000_000
# Share of the run budget the jobs fetch may use; the rest is for classify, FX and the write.
JOBS_FETCH_SHARE = 0.65
# Reject a jobs run when more than this share of fetched ads fail the row checks.
MAX_REJECTED_SHARE = 0.5

_KEYED_ENV = {
    "careerjet": "CAREERJET_API_KEY",
    "jooble": "JOOBLE_API_KEY",
    "web3career": "WEB3_CAREER_TOKEN",
}
_refresh_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {s: _refresh_lock for s in REFRESHABLE}


class RefreshSettings(Settings):
    """Read from the environment like the main settings (feature-local, optional)."""

    data_refresh_budget_s: int = 90


def budget_s() -> float:
    return float(min(300, max(10, RefreshSettings().data_refresh_budget_s)))


# ---------------------------------------------------------------------------
# Outbound HTTP: public https hosts only, timeouts, size caps
# ---------------------------------------------------------------------------


def _resolve(host: str) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]


def assert_public_https(url: str, resolve: Callable[[str], list[str]] = _resolve) -> None:
    """Refuse non-https URLs, IP literals, local names and hosts resolving to non-public IPs."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    local_name = host == "localhost" or host.endswith((".local", ".internal", ".localhost"))
    if (
        parts.scheme != "https"
        or not host
        or local_name
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
    ):
        raise httpx.UnsupportedProtocol("destination is not a public https host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise httpx.UnsupportedProtocol("IP-literal destinations are not allowed")
    try:
        addresses = resolve(host)
    except OSError as exc:
        raise httpx.ConnectError("host did not resolve") from exc
    if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
        raise httpx.UnsupportedProtocol("destination resolves to a non-public address")


def _guard(request: httpx.Request) -> None:
    from app.features.pathway import catalogue_sources
    from pipelines.jobs import boards

    allowed = {
        "learn.microsoft.com",
        "api.coursera.org",
        "api.bnm.gov.my",
        "storage.dosm.gov.my",
        "export.arxiv.org",
        "boards-api.greenhouse.io",
        "api.lever.co",
        "api.ashbyhq.com",
        "api.smartrecruiters.com",
        "himalayas.app",
        "jobicy.com",
        "remoteok.com",
        "remotive.com",
        "search.api.careerjet.net",
        "jooble.org",
        "web3.career",
    } | {board.host for board in boards.ALL if board.host}
    for group in ("COURSERA", "MANUAL", "FREE_MS", "FREE_DIGITAL", "BUNDLES"):
        allowed |= {urlsplit(row.url).hostname for row in getattr(catalogue_sources, group, ())}
    if request.url.host not in allowed:
        raise httpx.UnsupportedProtocol("destination is not an approved data source")
    assert_public_https(str(request.url))


def guarded_client() -> httpx.Client:
    """HTTP client whose every request, including redirect hops, passes the destination check."""
    return httpx.Client(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT},
        # A redirect must never forward a keyed board's credentials or request body.
        follow_redirects=False,
        event_hooks={"request": [_guard]},
    )


def _bounded_get_json(client: httpx.Client, deadline: float) -> Callable[[str, int], Any]:
    """`get_json(url, timeout)` for the catalogue sources, raising the urllib errors they expect."""

    def get_json(url: str, timeout_s: int) -> Any:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("time budget reached")
        accept = "application/json"
        if (urlsplit(url).hostname or "").endswith("bnm.gov.my"):
            accept = "application/vnd.BNM.API.v1+json"
        try:
            with client.stream(
                "GET", url, headers={"Accept": accept}, timeout=min(float(timeout_s), left)
            ) as response:
                if response.status_code >= 300:
                    raise urllib.error.HTTPError(
                        url,
                        response.status_code,
                        "error",
                        None,  # type: ignore[arg-type]
                        None,
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("time budget reached")
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError("response exceeds the size limit")
        except httpx.TimeoutException as exc:
            raise TimeoutError("request timed out") from exc
        except httpx.HTTPError as exc:
            raise urllib.error.URLError(type(exc).__name__) from exc
        return json.loads(bytes(body))

    return get_json


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    rows_fetched: int
    rows_upserted: int
    rows_rejected: int
    message: str
    boards_run: list[str] = field(default_factory=list)
    boards_skipped: list[str] = field(default_factory=list)


class RefreshFailed(Exception):
    """Nothing was written. `code` is a stable machine-readable reason."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        rows_fetched: int = 0,
        rows_rejected: int = 0,
        boards_run: list[str] | None = None,
        boards_skipped: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.rows_fetched = rows_fetched
        self.rows_rejected = rows_rejected
        self.boards_run = boards_run or []
        self.boards_skipped = boards_skipped or []


def _today() -> date:
    return datetime.now(UTC).date()


# ---------------------------------------------------------------------------
# Pipelines (each reuses the existing functions)
# ---------------------------------------------------------------------------


def _run_courses(started: float, budget: float) -> Outcome:
    from app.features.pathway import catalogue_sources as src
    from app.features.pathway import sync

    deadline = started + budget - 25.0  # leave time for the Coursera/FX tail and the write
    client = guarded_client()
    try:
        return _courses_with(client, deadline, src, sync)
    finally:
        client.close()


def _courses_with(client: httpx.Client, deadline: float, src: Any, sync: Any) -> Outcome:
    get_json = _bounded_get_json(client, deadline)
    try:
        payload = get_json(src.MSLEARN_API, 60)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise RefreshFailed(
            "fetch_failed", f"Microsoft Learn did not answer ({type(exc).__name__})."
        ) from exc
    today = _today()
    try:
        if not isinstance(payload, dict):
            raise ValueError("catalog response is not an object")
        rows = src.all_rows(payload, today, allow_missing=True)
        if len(src.from_mslearn(payload, today, allow_missing=True)) < len(src.CURATED) * 0.7:
            raise ValueError("Microsoft Learn returned too little of the expected catalogue")
    except (ValueError, KeyError, TypeError) as exc:
        raise RefreshFailed(
            "validation_failed", f"Catalogue payload rejected ({type(exc).__name__})."
        ) from exc

    def live_fx() -> tuple[float, date] | None:
        try:
            return src.fetch_fx("USD", get_json=get_json)
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            return None  # the stored rate is kept (documented sync behaviour)

    def coursera(slug: str) -> bool | None:
        if time.monotonic() >= deadline:
            return None  # unknown: facts refresh, retirement state is kept
        return src.coursera_status(slug, get_json=get_json)

    # Every upsert has a successful bounded course-URL read. A successful link check alone
    # never refreshes a manual fee/duration verification date; those facts remain dated.
    from app.features.data_refresh.course_checks import checked_rows

    rows = checked_rows(rows, client, deadline)
    if not rows:
        raise RefreshFailed(
            "fetch_failed", "No course URL could be verified; previous catalogue retained."
        )
    try:
        with repository.write_connection(deadline + 15) as conn:
            records, retired, _detail = sync._job(
                payload, today, coursera, live_fx(), rows_override=rows
            )(conn)
    except (ValueError, KeyError, TypeError) as exc:
        raise RefreshFailed(
            "validation_failed",
            "Course catalogue not updated; the last good catalogue stays live.",
            rows_fetched=len(rows),
            rows_rejected=len(rows),
        ) from exc
    return Outcome(
        rows_fetched=len(rows),
        rows_upserted=records,
        rows_rejected=max(0, len(rows) - records),
        message=f"{records} courses refreshed; {retired} retired.",
    )


def _run_labour(started: float, budget: float) -> Outcome:
    from pipelines.trends import malaysia_context as dosm

    try:
        with guarded_client() as client:
            deadline = started + budget - 15
            with client.stream(
                "GET", dosm.CSV_URL, timeout=max(1, deadline - time.monotonic())
            ) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("time budget reached")
                    body.extend(chunk)
                    if len(body) > dosm.MAX_BYTES:
                        raise ValueError("DOSM response exceeds the size limit")
        value = dosm.parse_latest(body.decode("utf-8-sig"), _today())
    except httpx.HTTPError as exc:
        raise RefreshFailed("fetch_failed", f"DOSM did not answer ({type(exc).__name__}).") from exc
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise RefreshFailed(
            "validation_failed",
            f"DOSM data rejected ({type(exc).__name__}).",
            rows_fetched=1,
            rows_rejected=1,
        ) from exc
    rates = (value.unemployment_rate, value.participation_rate, value.employment_population_ratio)
    if not all(0.0 <= r <= 100.0 for r in rates):
        raise RefreshFailed(
            "validation_failed", "A DOSM rate is outside 0-100%.", rows_fetched=1, rows_rejected=1
        )
    with repository.write_connection(started + budget - 5) as conn:
        dosm.publish(value, repository.bounded_db_url(), conn=conn)
    return Outcome(1, 1, 0, f"Labour force survey for {value.observed_month:%B %Y} stored.")


def selected_boards() -> tuple[list[Any], list[str]]:
    """Documented public employer APIs; optional keyed providers stay opt-in.

    Historical connectors remain available to the standalone CLI, but the automatic job
    does not use undocumented career-site endpoints or generic worldwide remote feeds.
    """
    from pipelines.jobs import boards

    keyed = {b.board for b in boards.KEYED}
    runnable: list[Any] = []
    skipped: list[str] = []
    for b in boards.ALL:
        if b.source not in {"greenhouse", "lever", "ashby", *_KEYED_ENV}:
            skipped.append(b.board)
            continue
        env = _KEYED_ENV.get(b.source)
        if b.board in keyed and env and not os.environ.get(env, "").strip():
            skipped.append(b.board)
        else:
            runnable.append(b)
    # Quick single-request feeds first; employer boards rotated so repeated runs that hit
    # the time budget do not always leave the same boards unread.
    quick = [b for b in runnable if b in boards.REMOTE or b.board in keyed]
    employers = [b for b in runnable if b not in quick]
    if employers:
        offset = secrets.randbelow(len(employers))
        employers = employers[offset:] + employers[:offset]
    return quick + employers, skipped


def _run_jobs(started: float, budget: float) -> Outcome:
    from pipelines.jobs import run as jobs_run
    from pipelines.jobs.sources import Fetcher

    selected, no_key = selected_boards()
    fetch_deadline = started + budget * JOBS_FETCH_SHARE
    client = guarded_client()
    try:
        raw, log_entries = jobs_run.fetch(
            None,
            selected=selected,
            fetcher=Fetcher(client=client, deadline=fetch_deadline),
            deadline=fetch_deadline,
        )
    finally:
        client.close()
    ran = [e["board"] for e in log_entries if e["status"] in ("ok", "partial")]
    skipped = no_key + [e["board"] for e in log_entries if e["status"] not in ("ok", "partial")]
    if not any(e["status"] == "ok" for e in log_entries) or not raw:
        raise RefreshFailed(
            "fetch_failed",
            "No job board answered with openings; the current openings stay live.",
            boards_run=ran,
            boards_skipped=skipped,
        )
    today = _today()
    # Automatic publication requires the posting's own location to identify Malaysia.
    # A generic "Worldwide" remote label alone does not establish Malaysian coverage.
    from pipelines.jobs.sources import in_malaysia

    raw = [posting for posting in raw if in_malaysia(posting.location)]
    rows = jobs_run.classify(raw, today)
    valid = [r for r in rows if r["title"] and str(r["url"]).startswith("https://")]
    rejected = len(rows) - len(valid)
    if not valid or rejected > len(rows) * MAX_REJECTED_SHARE:
        raise RefreshFailed(
            "validation_failed",
            "Too many fetched openings failed validation; nothing was written.",
            rows_fetched=len(rows),
            rows_rejected=len(rows),
            boards_run=ran,
            boards_skipped=skipped,
        )
    # Refresh openings only; certification prices have their own dated source records.
    # Avoid an unbounded extra FX request or silently re-verifying exam fees here.
    certs: list[dict[str, Any]] = []
    with repository.write_connection(started + budget - 5) as conn:
        active = jobs_run.to_db(
            valid, certs, log_entries, today, url=repository.bounded_db_url(), conn=conn
        )
    return Outcome(
        rows_fetched=len(rows),
        rows_upserted=len(valid),
        rows_rejected=rejected,
        message=f"{len(valid)} openings upserted from {len(ran)} boards; {active} active.",
        boards_run=ran,
        boards_skipped=skipped,
    )


def _run_trends(started: float, budget: float) -> Outcome:
    from app.features.trends import refresh as trends_refresh

    if time.monotonic() - started >= budget:
        raise TimeoutError("time budget reached")
    result = trends_refresh.rescore(deadline=started + budget)
    if result.status == "failed":
        raise RefreshFailed("validation_failed", result.message)
    # A re-score does not fetch papers. Keep observation/retrieval dates in the snapshot.
    rows = _trends().rows if result.status == "published" else 0
    return Outcome(rows, rows, 0, result.message)


_RUNNERS: dict[str, Callable[[float, float], Outcome]] = {
    "courses": _run_courses,
    "jobs": _run_jobs,
    "labour": _run_labour,
    "trends": _run_trends,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _storage_ready() -> bool:
    return refdata.use_postgres()


def _in_progress() -> AppError:
    return AppError(
        "This source is already being refreshed.", status_code=409, code="refresh_in_progress"
    )


def refresh(source: RefreshableSource) -> DataRefreshResult:
    if source == "catalogue":
        source = "courses"
    if not _storage_ready():
        raise AppError(
            "Live refresh writes to the app database (M3_BACKEND=postgres).",
            status_code=503,
            code="refresh_requires_database",
        )
    lock = _locks[source]
    if not lock.acquire(blocking=False):
        raise _in_progress()
    try:
        try:
            with repository.advisory_lock(source) as held:
                if not held:
                    raise _in_progress()
                return _execute(source)
        except psycopg.Error as exc:
            raise AppError(
                "The app database is unreachable; nothing was refreshed.",
                status_code=503,
                code="storage_unavailable",
            ) from exc
    finally:
        lock.release()


def _execute(
    source: RefreshableSource,
    *,
    runner: Callable[[float, float], Outcome] | None = None,
    limit: float | None = None,
) -> DataRefreshResult:
    started_at = datetime.now(UTC)
    started = time.monotonic()
    code: str | None = None
    try:
        outcome = (runner or _RUNNERS[source])(started, limit if limit is not None else budget_s())
    except ImportError:
        code = "refresh_not_supported"
        outcome = Outcome(0, 0, 0, "The source pipeline is not installed in this API process.")
    except RefreshFailed as exc:
        code = exc.code
        outcome = Outcome(
            exc.rows_fetched, 0, exc.rows_rejected, exc.message, exc.boards_run, exc.boards_skipped
        )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - reported as a failed run; transactions rolled back
        log.warning("data refresh %s failed: %s", source, type(exc).__name__)
        code = "refresh_failed"
        outcome = Outcome(
            0, 0, 0, f"Refresh failed ({type(exc).__name__}); the last good data stays live."
        )
    finished_at = datetime.now(UTC)
    status = "failed" if code else "ok"
    repository.record_run(
        source,
        started_at,
        finished_at,
        status,
        outcome.rows_fetched,
        outcome.rows_upserted,
        outcome.rows_rejected,
        code,
        code or "",
    )
    if code == "refresh_not_supported":
        raise AppError(outcome.message, status_code=501, code=code)
    if status == "ok":
        refdata.invalidate()
    return DataRefreshResult(
        source=source,
        status=status,  # type: ignore[arg-type]
        started_at=started_at,
        finished_at=finished_at,
        rows_fetched=outcome.rows_fetched,
        rows_upserted=outcome.rows_upserted,
        rows_rejected=outcome.rows_rejected,
        error_code=code,
        message=outcome.message,
        boards_run=outcome.boards_run,
        boards_skipped=outcome.boards_skipped,
        freshness=_one(source),
    )


# ---------------------------------------------------------------------------
# Freshness (stored data and run logs only)
# ---------------------------------------------------------------------------

_INFO: dict[str, tuple[str, str | None]] = {
    "courses": (
        "Course catalogue (Microsoft Learn Catalog API, Coursera, HRD Corp providers)",
        "https://learn.microsoft.com/en-us/training/support/catalog-api",
    ),
    "jobs": ("Public job feeds (employer career sites and remote job APIs)", None),
    "labour": (
        "Department of Statistics Malaysia: monthly Labour Force Survey",
        "https://open.dosm.gov.my/data-catalogue/lfs_month",
    ),
}
_Seeded = tuple[int, date | None, date | None]


def _day(value: object) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _seed_courses() -> _Seeded:
    rows = seed.rows("courses", "courses")
    days = [d for r in rows if (d := _day(r.get("verified_at")))]
    return len(rows), min(days, default=None), None


def _seed_jobs() -> _Seeded:
    rows = [r for r in seed.rows("jobs", "job_postings") if r.get("active", "true") == "true"]
    try:
        text = (seed.SEED_DIR / "jobs" / "fetch_log.json").read_text(encoding="utf-8")
        logged = _day(json.loads(text).get("fetched_on"))
    except (OSError, ValueError, AttributeError):
        logged = None
    seen = max((d for r in rows if (d := _day(r.get("last_seen")))), default=None)
    return len(rows), logged or seen, None


def _seed_labour() -> _Seeded:
    try:
        text = (seed.SEED_DIR / "trends" / "malaysia_labour.json").read_text(encoding="utf-8")
        data = json.loads(text)
        meta = data["meta"]
        return 1, _day(meta["sources"][0]["retrieved_at"]), _day(data.get("observed_month"))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return 0, None, None


_SEEDS: dict[str, Callable[[], _Seeded]] = {
    "courses": _seed_courses,
    "jobs": _seed_jobs,
    "labour": _seed_labour,
}


def _trends() -> DataSourceFreshness:
    from app.features.trends import service as trends_service

    name = "arXiv cs.AI listings scored by the trend pipeline"
    url: str | None = "https://arxiv.org/list/cs.AI/recent"
    try:
        snap = trends_service.get_snapshot(None, "moderate")
    except Exception:  # noqa: BLE001 - freshness must still answer for the other sources
        return DataSourceFreshness(
            source="trends",
            source_name=name,
            source_url=url,
            rows=0,
            served_from="seed",
            is_fallback=True,
            refreshable=False,
        )
    if snap.meta.sources:
        name, url = snap.meta.sources[0].name, snap.meta.sources[0].url or url
    from_db = snap.meta.served_from == "db"
    return DataSourceFreshness(
        source="trends",
        source_name=name,
        source_url=url,
        last_fetched_at=max((s.retrieved_at for s in snap.meta.sources), default=None),
        data_as_of=snap.meta.observed_to,
        snapshot_date=snap.meta.snapshot_date,
        observed_from=snap.meta.observed_from,
        observed_to=snap.meta.observed_to,
        is_historical_replay=bool(
            snap.meta.observed_to
            and snap.meta.observed_to < snap.meta.snapshot_date - timedelta(days=60)
        ),
        rows=len(snap.items),
        served_from="database" if from_db else "seed",
        is_fallback=snap.meta.is_fallback or not from_db,
        refreshable=True,
    )


def _one(source: DataSourceId) -> DataSourceFreshness:
    if source == "trends":
        return _trends()
    name, url = _INFO[source]
    stored = repository.stored_freshness(source)
    if stored is not None:
        rows, fetched, as_of = stored.rows, stored.last_fetched_at, stored.data_as_of
    else:
        rows, fetched, as_of = _SEEDS[source]()
    return DataSourceFreshness(
        source=source,
        source_name=name,
        source_url=url,
        last_fetched_at=fetched,
        data_as_of=as_of,
        rows=rows,
        served_from="database" if stored is not None else "seed",
        is_fallback=stored is None,
        refreshable=True,
    )


def freshness() -> DataFreshnessResponse:
    runs = repository.last_runs()
    successes = repository.last_successes()
    today = _today()
    sources: tuple[DataSourceId, ...] = ("trends", "courses", "jobs", "labour")
    items = []
    for source in sources:
        item = _one(source)
        observed = item.data_as_of or item.last_fetched_at
        age = max(0, (today - observed).days) if observed else None
        items.append(
            item.model_copy(
                update={
                    "last_run": runs.get(source),
                    "last_success": successes.get(source),
                    "last_checked_at": runs[source].finished_at if source in runs else None,
                    "age_days": age,
                    "is_stale": source == "trends"
                    and (
                        item.is_fallback
                        or item.is_historical_replay
                        or age is None
                        or age > RefreshSettings().trends_stale_days
                    ),
                }
            )
        )
    return DataFreshnessResponse(sources=items)
