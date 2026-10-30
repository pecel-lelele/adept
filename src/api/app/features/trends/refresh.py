"""Admin trend refresh (F2): fetch the latest data on demand, or re-score what is stored.

1. Fetch latest data. The real refresh is the `trends-refresh.yml` GitHub Actions workflow:
   it ingests arXiv cs.AI through the MiniLM RunPod worker, scores, validates and publishes a
   dated snapshot to the deployment database (the workflow's TREND_DATABASE_URL secret is the
   same database the app reads as DATABASE_URL). `dispatch()` starts it through the GitHub REST
   API (workflow_dispatch) with a server-side GITHUB_DISPATCH_TOKEN that never reaches the
   browser. `status()` polls the run; once it completes successfully the app's trend caches
   are cleared so the new snapshot is served within seconds instead of after the cache TTL.
   One run at a time: while a run is queued or in progress, it is returned instead.
2. Re-score now. `rescore()` re-scores the latest stored arXiv signals in process with the
   pipeline's own pure scorer, validator and publisher (no ingest, no model call). It publishes
   only when the result differs from the latest published snapshot (another measured window);
   otherwise it reports "no new data" and creates nothing.

Both need an account whose stable ID is listed in ADMIN_USER_IDS (the same list the web admin pages
use), checked here on the server from the signed session; an empty list allows nobody.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.contracts.trends import TrendRefreshStatus, TrendRescoreResult
from app.core.admin import require_admin as require_admin
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger("app.trends.refresh")

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT_S = 10.0
# After a dispatch GitHub takes a few seconds to list the run; wait this long for it here.
FIND_RUN_WINDOW_S = 6.0
FIND_RUN_INTERVAL_S = 1.5
# A dispatch whose run has not been listed yet still counts as running for this long.
PENDING_DISPATCH_S = 120.0
ACTIVE = {"queued", "in_progress", "waiting", "requested", "pending"}
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_WORKFLOW = re.compile(r"[A-Za-z0-9_.-]+\.ya?ml")
_REF = re.compile(r"[A-Za-z0-9_./-]{1,100}")


class RefreshSettings(Settings):
    """Read from the environment / root .env like the main settings (feature-local)."""

    github_dispatch_token: str = ""
    github_repository: str = ""
    github_workflow: str = "trends-refresh.yml"
    github_dispatch_ref: str = "main"


def settings() -> RefreshSettings:
    return RefreshSettings()


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Cache invalidation after a publish
# ---------------------------------------------------------------------------


def clear_trend_caches() -> None:
    """Forget every in-process copy of trend data so the newest snapshot is read next."""
    from app.features.matching import trend_port as matching_trend_port
    from app.features.pathway import trend_port as pathway_trend_port
    from app.features.trends import repository, service

    service.clear_cache()
    repository._reset_db_cache()
    matching_trend_port.reset_down()
    pathway_trend_port.reset_cache()


def _served_snapshot() -> dict[str, Any]:
    from app.features.trends import service

    try:
        snap = service.get_snapshot(None, "moderate")
    except Exception:  # noqa: BLE001 - status still reports the run; the date is optional
        return {}
    return {
        "snapshot_date": snap.meta.snapshot_date,
        "served_from": snap.meta.served_from,
        "is_fallback": snap.meta.is_fallback,
    }


# ---------------------------------------------------------------------------
# GitHub Actions dispatch
# ---------------------------------------------------------------------------

_dispatch_lock = threading.Lock()  # one dispatch request at a time
_lock = threading.Lock()  # guards the bookkeeping below
_pending_since: datetime | None = None  # dispatched, run not listed yet
_cleared_runs: set[int] = set()


def reset_state() -> None:
    """Forget dispatch bookkeeping (between tests)."""
    global _pending_since
    with _lock:
        _pending_since = None
        _cleared_runs.clear()


def _configured(cfg: RefreshSettings) -> tuple[str, str, str]:
    if not cfg.github_dispatch_token.strip() or not cfg.github_repository.strip():
        raise AppError(
            "Fetching the latest trend data is not configured on this server "
            "(GITHUB_DISPATCH_TOKEN / GITHUB_REPOSITORY). Run the 'Trends refresh' workflow "
            "manually from the repository's GitHub Actions tab.",
            status_code=503,
            code="refresh_not_configured",
        )
    repo, workflow, ref = (
        cfg.github_repository.strip(),
        cfg.github_workflow.strip(),
        cfg.github_dispatch_ref.strip(),
    )
    if not (_REPOSITORY.fullmatch(repo) and _WORKFLOW.fullmatch(workflow) and _REF.fullmatch(ref)):
        raise AppError(
            "GITHUB_REPOSITORY, GITHUB_WORKFLOW or GITHUB_DISPATCH_REF is malformed.",
            status_code=503,
            code="refresh_not_configured",
        )
    return repo, workflow, ref


def _client(token: str) -> httpx.Client:
    """GitHub API client; the token only ever goes to api.github.com, never via a redirect."""
    return httpx.Client(
        base_url=GITHUB_API,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "adept-trend-refresh",
        },
        timeout=REQUEST_TIMEOUT_S,
        follow_redirects=False,
    )


def _github_error(exc: Exception) -> AppError:
    log.warning("GitHub trend refresh call failed: %s", type(exc).__name__)
    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
    detail = f" (HTTP {status})" if status else ""
    return AppError(
        f"GitHub did not accept the trend refresh request{detail}. The last published "
        "snapshot stays live.",
        status_code=502,
        code="refresh_upstream_error",
    )


def _runs(client: httpx.Client, repo: str, workflow: str) -> list[dict[str, Any]]:
    response = client.get(
        f"/repos/{repo}/actions/workflows/{workflow}/runs",
        params={"per_page": 10, "branch": settings().github_dispatch_ref},
    )
    response.raise_for_status()
    runs = response.json().get("workflow_runs", [])
    return [
        r
        for r in runs
        if isinstance(r, dict)
        and r.get("head_branch", settings().github_dispatch_ref) == settings().github_dispatch_ref
    ]


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _since(runs: list[dict[str, Any]], moment: datetime) -> dict[str, Any] | None:
    """The newest manually dispatched run created at or after `moment` (5 s clock skew)."""
    floor = moment - timedelta(seconds=5)
    found = [
        r
        for r in runs
        if r.get("event") == "workflow_dispatch"
        and (created := _parse_time(r.get("created_at"))) is not None
        and created >= floor
    ]
    return max(found, key=lambda r: str(r.get("created_at")), default=None)


def _status(run: dict[str, Any] | None, **extra: Any) -> TrendRefreshStatus:
    if run is None:
        return TrendRefreshStatus(status="queued", **extra)
    raw = str(run.get("status") or "queued")
    status = raw if raw in {"completed", "in_progress"} else "queued"
    run_id = run.get("id") if isinstance(run.get("id"), int) else None
    url = run.get("html_url")
    result = TrendRefreshStatus(
        status=status,  # type: ignore[arg-type]
        conclusion=run.get("conclusion") if isinstance(run.get("conclusion"), str) else None,
        run_id=run_id,
        run_url=url if isinstance(url, str) and url.startswith("https://github.com/") else None,
        created_at=run.get("created_at") if isinstance(run.get("created_at"), str) else None,
        updated_at=run.get("updated_at") if isinstance(run.get("updated_at"), str) else None,
        **extra,
    )
    if result.status == "completed" and result.conclusion == "success" and run_id is not None:
        with _lock:
            first = run_id not in _cleared_runs
            _cleared_runs.add(run_id)
        if first:
            clear_trend_caches()
        result.caches_cleared = True
        result = result.model_copy(update=_served_snapshot())
    return result


def dispatch() -> TrendRefreshStatus:
    """Start the trends-refresh workflow unless a run is already queued or in progress."""
    global _pending_since
    cfg = settings()
    repo, workflow, ref = _configured(cfg)
    if not _dispatch_lock.acquire(blocking=False):
        raise AppError(
            "A trend refresh request is already being submitted.",
            status_code=409,
            code="refresh_in_progress",
        )
    try:
        with _client(cfg.github_dispatch_token.strip()) as client:
            runs = _runs(client, repo, workflow)
            active = next((r for r in runs if r.get("status") in ACTIVE), None)
            if active is not None:
                return _status(active, already_running=True)
            now = datetime.now(UTC)
            with _lock:
                pending = _pending_since
            if pending is not None and now - pending < timedelta(seconds=PENDING_DISPATCH_S):
                return _status(_since(runs, pending), already_running=True)
            response = client.post(
                f"/repos/{repo}/actions/workflows/{workflow}/dispatches", json={"ref": ref}
            )
            response.raise_for_status()
            with _lock:
                _pending_since = now
            started = time.monotonic()
            run = None
            while time.monotonic() - started < FIND_RUN_WINDOW_S:
                time.sleep(FIND_RUN_INTERVAL_S)
                run = _since(_runs(client, repo, workflow), now)
                if run is not None:
                    with _lock:
                        _pending_since = None
                    break
            return _status(run, dispatched=True)
    except httpx.HTTPError as exc:
        raise _github_error(exc) from exc
    finally:
        _dispatch_lock.release()


def status(run_id: int | None = None) -> TrendRefreshStatus:
    """The given run, else the run this server last dispatched, else the latest manual run."""
    global _pending_since
    cfg = settings()
    repo, workflow, _ = _configured(cfg)
    try:
        with _client(cfg.github_dispatch_token.strip()) as client:
            if run_id is not None:
                response = client.get(f"/repos/{repo}/actions/runs/{run_id}")
                response.raise_for_status()
                run = response.json()
                if not isinstance(run, dict) or run.get("workflow_id") is None:
                    raise AppError("Unknown workflow run.", status_code=404, code="not_found")
                if not str(run.get("path", "")).endswith(f"/{workflow}"):
                    raise AppError("Unknown workflow run.", status_code=404, code="not_found")
                return _status(run)
            runs = _runs(client, repo, workflow)
            with _lock:
                pending = _pending_since
            if pending is not None:
                run = _since(runs, pending)
                if run is not None:
                    with _lock:
                        _pending_since = None
                return _status(run)
            manual = [r for r in runs if r.get("event") == "workflow_dispatch"]
            latest = max(manual, key=lambda r: str(r.get("created_at")), default=None)
            if latest is None:
                raise AppError("No trend refresh run yet.", status_code=404, code="not_found")
            return _status(latest)
    except httpx.HTTPError as exc:
        raise _github_error(exc) from exc


# ---------------------------------------------------------------------------
# Re-score stored signals (in process, no ingest, no model call)
# ---------------------------------------------------------------------------

_rescore_lock = threading.Lock()
# Bound every pipeline query issued from the API process.
RESCORE_CONNECT_TIMEOUT_S = 5
RESCORE_STATEMENT_TIMEOUT_MS = 15000


def _bounded_db_url() -> str:
    from psycopg.conninfo import make_conninfo

    from app.core.config import get_settings

    return make_conninfo(
        get_settings().database_url,
        connect_timeout=RESCORE_CONNECT_TIMEOUT_S,
        options=(f"-c statement_timeout={RESCORE_STATEMENT_TIMEOUT_MS} -c lock_timeout=5000"),
    )


def latest_published(db_url: str) -> tuple[date, str | None] | None:
    """Date and provenance note of the newest published snapshot."""
    import psycopg

    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT s.snapshot_date, m.provenance_note FROM "
            "(SELECT max(snapshot_date) AS snapshot_date FROM trend_snapshots) s "
            "LEFT JOIN trend_snapshot_meta m ON m.snapshot_date = s.snapshot_date"
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row and row[0] else None


def _today() -> date:
    return date.today()


def rescore() -> TrendRescoreResult:
    """Re-score the latest two stored weeks; publish only a genuinely new snapshot."""
    if not _rescore_lock.acquire(blocking=False):
        raise AppError(
            "A re-score is already running.", status_code=409, code="refresh_in_progress"
        )
    try:
        try:
            from pipelines.trends import run as pipeline
            from pipelines.trends import score
        except ImportError as exc:  # the API was started without src/ on PYTHONPATH
            raise AppError(
                "The trend scorer is not installed in this API process.",
                status_code=503,
                code="rescore_unavailable",
            ) from exc
        try:
            return _rescore(pipeline, score, _bounded_db_url())
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001 - reported; nothing was published
            log.warning("trend re-score failed: %s", type(exc).__name__)
            return TrendRescoreResult(
                status="failed",
                message=(
                    f"Re-score failed ({type(exc).__name__}); nothing was published and the "
                    "last snapshot stays live."
                ),
            )
    finally:
        _rescore_lock.release()


def _rescore(pipeline: Any, score: Any, db_url: str) -> TrendRescoreResult:
    from app.features.trends.provenance import window_from_note

    latest = latest_published(db_url)
    live = latest[0] if latest else None
    periods = score.list_available_periods(db_url)
    if len(periods) < 2:
        return TrendRescoreResult(
            status="no_new_data",
            message="Fewer than two weeks of arXiv signals are stored; nothing to re-score.",
            snapshot_date=live,
        )
    t0, t1 = periods[-2], periods[-1]
    t0_dates = pipeline.collected_dates(db_url, t0)
    t1_dates = pipeline.collected_dates(db_url, t1)
    if t0_dates is None or t1_dates is None:
        return TrendRescoreResult(
            status="failed",
            message="Signal collection dates are missing; nothing was published.",
            snapshot_date=live,
        )
    sources, note = pipeline.provenance(t0, t1, t0_dates, t1_dates)
    observed = window_from_note(note)
    if latest is not None and latest[1] == note:
        return TrendRescoreResult(
            status="no_new_data",
            message=(
                f"No new data: snapshot {latest[0].isoformat()} already measures the stored "
                "signals. Fetch the latest data to ingest a new arXiv listing."
            ),
            snapshot_date=live,
            observed_from=observed[0],
            observed_to=observed[1],
        )
    today = _today()
    if live is not None and live >= today:
        return TrendRescoreResult(
            status="no_new_data",
            message=(
                f"Snapshot {live.isoformat()} was already published today; it is not replaced "
                "from stored signals."
            ),
            snapshot_date=live,
        )
    counts_t0, total_t0 = score.load_signal_raw(db_url, t0)
    counts_t1, total_t1 = score.load_signal_raw(db_url, t1)
    skill_ids = score.load_skill_ids(db_url)
    rows = score.score_rows(
        counts_t0,
        total_t0,
        counts_t1,
        total_t1,
        score.load_labor_decay(),
        score.load_automation_exposure(),
        skill_ids=skill_ids,
    )
    evidenced = [r for r in rows if r.get("has_evidence", True)]
    errors = pipeline.validate(evidenced, skill_ids, t0, t1)
    if errors:
        return TrendRescoreResult(
            status="failed",
            message="Snapshot failed validation and was not published: " + "; ".join(errors[:3]),
            snapshot_date=live,
        )
    pipeline.publish(evidenced, today, sources, note, db_url)
    clear_trend_caches()
    return TrendRescoreResult(
        status="published",
        message=f"Published snapshot {today.isoformat()} from stored signals ({t1} vs {t0}).",
        snapshot_date=today,
        observed_from=observed[0],
        observed_to=observed[1],
    )
