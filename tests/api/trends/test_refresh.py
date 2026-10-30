"""Admin trend refresh: GitHub workflow dispatch (mocked API) and in-process re-score.

No network, database, GitHub token or model: GitHub is an httpx.MockTransport, the pipeline's
database helpers are in-memory fakes, and the scorer/validator/provenance are production code.
"""

from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from harness import fixtures

from app.core import accounts
from app.core.config import get_settings
from app.features.trends import refresh
from app.features.trends import service as trends_service

ADMIN = accounts.Account("synthetic-admin", "Synthetic Admin", "admin@example.test", "learner")
REPO = "example-org/adept"
TOKEN = "synthetic-dispatch-token"


class FakeGitHub:
    """Minimal GitHub Actions API: runs list, run detail and workflow_dispatch."""

    def __init__(self, runs: list[dict[str, Any]] | None = None) -> None:
        self.runs = runs or []
        self.dispatches: list[dict[str, Any]] = []
        self.requests: list[httpx.Request] = []
        self.fail_dispatch = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.url.host == "api.github.com"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        path = request.url.path
        if path == f"/repos/{REPO}/actions/workflows/trends-refresh.yml/runs":
            return httpx.Response(200, json={"workflow_runs": self.runs})
        if path == f"/repos/{REPO}/actions/workflows/trends-refresh.yml/dispatches":
            if self.fail_dispatch:
                return httpx.Response(422, json={"message": "synthetic failure"})
            self.dispatches.append(json.loads(request.content))
            self.runs.insert(0, run(len(self.runs) + 100, "queued"))
            return httpx.Response(204)
        if path.startswith(f"/repos/{REPO}/actions/runs/"):
            run_id = int(path.rsplit("/", 1)[-1])
            found = next((r for r in self.runs if r["id"] == run_id), None)
            return httpx.Response(200, json=found) if found else httpx.Response(404)
        return httpx.Response(404)


def run(run_id: int, status: str, conclusion: str | None = None) -> dict[str, Any]:
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "id": run_id,
        "status": status,
        "conclusion": conclusion,
        "event": "workflow_dispatch",
        "html_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
        "created_at": now,
        "updated_at": now,
        "workflow_id": 1,
        "path": ".github/workflows/trends-refresh.yml",
    }


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub()
    real = httpx.Client
    monkeypatch.setattr(
        refresh,
        "_client",
        lambda token: real(
            base_url=refresh.GITHUB_API,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.MockTransport(fake),
        ),
    )
    monkeypatch.setattr(refresh.time, "sleep", lambda _s: None)
    monkeypatch.setattr(refresh, "FIND_RUN_WINDOW_S", 0.5)
    return fake


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = refresh.RefreshSettings(
        github_dispatch_token=TOKEN,
        github_repository=REPO,
    )
    monkeypatch.setattr(refresh, "settings", lambda: cfg)
    monkeypatch.setattr(get_settings(), "admin_user_ids", ADMIN.id)


@pytest.fixture(autouse=True)
def _admin_account() -> Any:
    refresh.reset_state()
    accounts.create(ADMIN, "")
    yield
    refresh.reset_state()
    fixtures.install()


AS_ADMIN = {"X-Demo-User": ADMIN.id}


def test_matching_admin_email_does_not_grant_a_different_account_access(
    client: TestClient,
    configured: None,
    github: FakeGitHub,
) -> None:
    impersonator = accounts.Account("synthetic-other-id", "Synthetic Other", ADMIN.email, "learner")
    accounts.reset()  # An email claimant registered before the configured account existed.
    accounts.create(impersonator, "")
    response = client.post("/api/v1/trends/refresh", headers={"X-Demo-User": impersonator.id})
    assert response.status_code == 403
    assert github.requests == []


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/trends/refresh"),
        ("get", "/api/v1/trends/refresh/status"),
        ("post", "/api/v1/trends/refresh/rescore"),
    ],
)
def test_unknown_session_is_401_and_non_admin_is_403(
    client: TestClient, configured: None, github: FakeGitHub, method: str, path: str
) -> None:
    unknown = getattr(client, method)(path, headers={"X-Demo-User": "v2.not-a-real-token"})
    assert unknown.status_code == 401
    learner = getattr(client, method)(path, headers={"X-Demo-User": "aisyah"})
    assert learner.status_code == 403
    assert github.requests == []


def test_empty_admin_list_allows_nobody(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, github: FakeGitHub
) -> None:
    cfg = refresh.RefreshSettings(github_dispatch_token=TOKEN, github_repository=REPO)
    monkeypatch.setattr(refresh, "settings", lambda: cfg)
    assert client.post("/api/v1/trends/refresh", headers=AS_ADMIN).status_code == 403
    assert github.dispatches == []


# ---------------------------------------------------------------------------
# Fetch latest data (workflow_dispatch)
# ---------------------------------------------------------------------------


def test_missing_token_is_503_refresh_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, github: FakeGitHub
) -> None:
    cfg = refresh.RefreshSettings(github_dispatch_token="")
    monkeypatch.setattr(get_settings(), "admin_user_ids", ADMIN.id)
    monkeypatch.setattr(refresh, "settings", lambda: cfg)
    response = client.post("/api/v1/trends/refresh", headers=AS_ADMIN)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "refresh_not_configured"
    assert github.requests == []


def test_dispatch_starts_one_run_and_never_returns_the_token(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    response = client.post("/api/v1/trends/refresh", headers=AS_ADMIN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dispatched"] is True and body["already_running"] is False
    assert body["status"] == "queued" and body["run_id"] == 100
    assert body["run_url"] == f"https://github.com/{REPO}/actions/runs/100"
    assert github.dispatches == [{"ref": "main"}]
    assert TOKEN not in response.text


def test_running_workflow_is_returned_instead_of_dispatching(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    github.runs = [run(7, "in_progress")]
    body = client.post("/api/v1/trends/refresh", headers=AS_ADMIN).json()
    assert body["already_running"] is True and body["dispatched"] is False
    assert body["run_id"] == 7 and body["status"] == "in_progress"
    assert github.dispatches == []


def test_second_request_while_one_is_submitting_is_409(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    assert refresh._dispatch_lock.acquire(blocking=False)
    try:
        response = client.post("/api/v1/trends/refresh", headers=AS_ADMIN)
    finally:
        refresh._dispatch_lock.release()
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "refresh_in_progress"
    assert github.dispatches == []


def test_dispatch_rejected_by_github_is_502_and_changes_nothing(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    github.fail_dispatch = True
    response = client.post("/api/v1/trends/refresh", headers=AS_ADMIN)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "refresh_upstream_error"
    assert TOKEN not in response.text


def test_completed_success_clears_caches_once(
    client: TestClient, configured: None, github: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    cleared: list[int] = []
    monkeypatch.setattr(refresh, "clear_trend_caches", lambda: cleared.append(1))
    github.runs = [run(42, "completed", "success")]
    for _ in range(2):
        response = client.get(
            "/api/v1/trends/refresh/status", params={"run_id": 42}, headers=AS_ADMIN
        )
        body = response.json()
        assert body["status"] == "completed" and body["conclusion"] == "success"
        assert body["caches_cleared"] is True
        assert body["snapshot_date"] is not None
    assert cleared == [1]


def test_completed_failure_keeps_the_last_snapshot(
    client: TestClient, configured: None, github: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(refresh, "clear_trend_caches", lambda: pytest.fail("cleared caches"))
    github.runs = [run(43, "completed", "failure")]
    body = client.get("/api/v1/trends/refresh/status", headers=AS_ADMIN).json()
    assert body["status"] == "completed" and body["conclusion"] == "failure"
    assert body["caches_cleared"] is False and body["snapshot_date"] is None


def test_status_follows_the_dispatched_run(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    client.post("/api/v1/trends/refresh", headers=AS_ADMIN)
    github.runs[0]["status"] = "in_progress"
    assert client.get("/api/v1/trends/refresh/status", headers=AS_ADMIN).json()["run_id"] == 100


def test_run_of_another_workflow_is_not_reported(
    client: TestClient, configured: None, github: FakeGitHub
) -> None:
    other = run(9, "completed", "success")
    other["path"] = ".github/workflows/ci.yml"
    github.runs = [other]
    response = client.get("/api/v1/trends/refresh/status", params={"run_id": 9}, headers=AS_ADMIN)
    assert response.status_code == 404


def test_new_snapshot_reaches_replan_and_radar_after_success(
    client: TestClient, configured: None, github: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After the workflow publishes, the re-plan check and radar see the new date at once."""
    from app.features.pathway import trend_port as pathway_trend_port

    pathway_trend_port.reset_cache()
    original = trends_service.last_good_snapshot
    old = original(None, "moderate").meta.snapshot_date
    assert pathway_trend_port.latest_version() == f"m1-{old.isoformat()}"
    new = old + timedelta(days=7)
    published = threading.Event()

    def source(snapshot_date: date | None, scenario: str, **kw: Any) -> Any:
        if not published.is_set() or snapshot_date not in (None, new):
            return original(snapshot_date, scenario, **kw)
        snap = original(None, scenario, **kw)
        dates = [*snap.meta.available_snapshots, new]
        return snap.model_copy(
            update={
                "meta": snap.meta.model_copy(
                    update={"snapshot_date": new, "available_snapshots": dates}
                )
            }
        )

    monkeypatch.setattr(trends_service, "last_good_snapshot", source)
    published.set()  # the workflow published; the app still holds cached copies
    assert pathway_trend_port.latest_version() == f"m1-{old.isoformat()}"

    github.runs = [run(50, "completed", "success")]
    body = client.get(
        "/api/v1/trends/refresh/status", params={"run_id": 50}, headers=AS_ADMIN
    ).json()
    assert body["snapshot_date"] == new.isoformat()
    assert pathway_trend_port.latest_version() == f"m1-{new.isoformat()}"
    radar = client.get("/api/v1/trends/snapshot").json()
    assert radar["meta"]["snapshot_date"] == new.isoformat()


# ---------------------------------------------------------------------------
# Re-score stored signals
# ---------------------------------------------------------------------------


def _fake_pipeline(
    published: list[tuple[date, str]],
    periods: list[str] | None = None,
    skills: int | None = None,
) -> tuple[SimpleNamespace, SimpleNamespace]:
    from pipelines.trends import run as real_run
    from pipelines.trends import score as real_score

    exposure = real_score.load_automation_exposure()
    skill_ids = set(sorted(exposure)[: skills or len(exposure)])
    week = {
        "2026-W43": (date(2026, 10, 19), date(2026, 10, 25)),
        "2026-W44": (date(2026, 10, 26), date(2026, 10, 29)),
    }
    pipeline = SimpleNamespace(
        provenance=real_run.provenance,
        validate=real_run.validate,
        collected_dates=lambda _url, period: week.get(period),
        publish=lambda rows, day, sources, note, _url: published.append((day, note)),
    )
    score = SimpleNamespace(
        list_available_periods=lambda _url: periods if periods is not None else list(week),
        load_signal_raw=lambda _url, period: (
            {sid: (i % 7) + (3 if period.endswith("44") else 1) for i, sid in enumerate(skill_ids)},
            200,
        ),
        load_skill_ids=lambda _url: skill_ids,
        score_rows=real_score.score_rows,
        load_labor_decay=real_score.load_labor_decay,
        load_automation_exposure=real_score.load_automation_exposure,
    )
    return pipeline, score


def test_rescore_publishes_a_genuinely_new_window(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[tuple[date, str]] = []
    cleared: list[int] = []
    monkeypatch.setattr(refresh, "latest_published", lambda _url: (date(2026, 10, 20), "older"))
    monkeypatch.setattr(refresh, "_today", lambda: date(2026, 10, 30))
    monkeypatch.setattr(refresh, "clear_trend_caches", lambda: cleared.append(1))
    pipeline, score = _fake_pipeline(published)
    result = refresh._rescore(pipeline, score, "synthetic")
    assert result.status == "published" and result.snapshot_date == date(2026, 10, 29)
    assert (result.observed_from, result.observed_to) == (date(2026, 10, 26), date(2026, 10, 29))
    assert [day for day, _ in published] == [date(2026, 10, 29)] and cleared == [1]


def test_rescore_of_already_published_signals_is_no_new_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.trends import run as real_run

    published: list[tuple[date, str]] = []
    _, note = real_run.provenance(
        "2026-W43",
        "2026-W44",
        (date(2026, 10, 19), date(2026, 10, 25)),
        (date(2026, 10, 26), date(2026, 10, 29)),
    )
    monkeypatch.setattr(refresh, "latest_published", lambda _url: (date(2026, 10, 29), note))
    monkeypatch.setattr(refresh, "clear_trend_caches", lambda: pytest.fail("cleared caches"))
    pipeline, score = _fake_pipeline(published)
    result = refresh._rescore(pipeline, score, "synthetic")
    assert result.status == "no_new_data" and result.snapshot_date == date(2026, 10, 29)
    assert published == []


def test_rescore_needs_two_weeks(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[tuple[date, str]] = []
    monkeypatch.setattr(refresh, "latest_published", lambda _url: None)
    pipeline, score = _fake_pipeline(published, periods=["2026-W44"])
    assert refresh._rescore(pipeline, score, "synthetic").status == "no_new_data"
    assert published == []


def test_rescore_cannot_relabel_historical_signals_as_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published: list[tuple[date, str]] = []
    note = "Historical arXiv window 2024-10-13..2024-10-19 replayed under 2026 dates."
    monkeypatch.setattr(refresh, "latest_published", lambda _url: (date(2026, 10, 20), note))
    pipeline, score = _fake_pipeline(published)
    result = refresh._rescore(pipeline, score, "synthetic")
    assert result.status == "failed" and published == []
    assert result.observed_to == date(2024, 10, 19)
    assert "Historical replay" in result.message


def test_expired_rescore_budget_does_not_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[tuple[date, str]] = []
    monkeypatch.setattr(refresh, "latest_published", lambda _url: (date(2026, 10, 20), "older"))
    pipeline, score = _fake_pipeline(published)
    result = refresh._rescore(pipeline, score, "synthetic", deadline=0)
    assert result.status == "failed" and published == []


def test_rescore_invalid_snapshot_is_not_published(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[tuple[date, str]] = []
    monkeypatch.setattr(refresh, "latest_published", lambda _url: (date(2026, 10, 20), "older"))
    monkeypatch.setattr(refresh, "_today", lambda: date(2026, 10, 30))
    pipeline, score = _fake_pipeline(published, skills=10)  # below MIN_SKILLS
    result = refresh._rescore(pipeline, score, "synthetic")
    assert result.status == "failed" and published == []
    assert result.snapshot_date == date(2026, 10, 20)


def test_rescore_failure_is_reported_and_concurrent_rescore_is_409(
    client: TestClient, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: Any) -> Any:
        raise OSError("synthetic database outage")

    monkeypatch.setattr(refresh, "_rescore", broken)
    body = client.post("/api/v1/trends/refresh/rescore", headers=AS_ADMIN).json()
    assert body["status"] == "failed" and "nothing was published" in body["message"]

    assert refresh._rescore_lock.acquire(blocking=False)
    try:
        response = client.post("/api/v1/trends/refresh/rescore", headers=AS_ADMIN)
    finally:
        refresh._rescore_lock.release()
    assert response.status_code == 409


def test_ci_workflow_name_cannot_override_the_app_refresh_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
    monkeypatch.delenv("TRENDS_REFRESH_WORKFLOW", raising=False)
    assert refresh.RefreshSettings(_env_file=None).trends_refresh_workflow == "trends-refresh.yml"
    monkeypatch.setenv("TRENDS_REFRESH_WORKFLOW", "synthetic-refresh.yml")
    assert (
        refresh.RefreshSettings(_env_file=None).trends_refresh_workflow == "synthetic-refresh.yml"
    )
