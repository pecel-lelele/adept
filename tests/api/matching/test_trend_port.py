"""Tests for Prompt 2 of PR-#4 review: in-process trend call, no HTTP, timeout guard.

Rules tested:
1. No HTTP library (httpx / requests) is ever called during a match request.
2. A slow snapshot getter (sleeps past the timeout) returns 503 quickly.
3. 30 concurrent match requests with a fake getter all complete without deadlock.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.contracts.trends import TrendSnapshotResponse
from app.features.matching.trend_port import TrendSnapshot
from app.features.trends import mocks as trends_mocks

# ---------------------------------------------------------------------------
# Shared fake snapshot (same shape as in test_snapshot_meta.py)
# ---------------------------------------------------------------------------

_SNAP_DATE = date(2026, 10, 20)
_GOOD_SNAPSHOT = TrendSnapshot(
    velocities={"python": 0.8, "sql": 0.5},
    snapshot_date=_SNAP_DATE,
    sources=[Source(name="O*NET 28.2", url="https://www.onetcenter.org/", retrieved_at=_SNAP_DATE)],
    scenario="moderate",
    is_estimate=True,
)

_FETCH_PATCH = "app.features.matching.service.fetch_snapshot"


def _fake_fetch_good(scenario: str) -> TrendSnapshot:  # noqa: ARG001
    return _GOOD_SNAPSHOT


# ---------------------------------------------------------------------------
# Test 1: No HTTP library is called
# ---------------------------------------------------------------------------


def test_no_http_call_during_match_request(client: TestClient) -> None:
    """httpx and requests must never be imported / called during a match request.

    We monkeypatch both libraries to raise if any attribute is accessed,
    then assert the endpoint still returns 200.
    """
    bomb = MagicMock()
    bomb.get.side_effect = AssertionError("httpx.get was called — HTTP call detected!")
    bomb.Client.side_effect = AssertionError("httpx.Client was called — HTTP call detected!")
    bomb.Session.side_effect = AssertionError("requests.Session was called — HTTP call detected!")

    with (
        patch("app.features.matching.service.fetch_snapshot", side_effect=_fake_fetch_good),
        patch.dict("sys.modules", {"httpx": bomb, "requests": bomb}),
    ):
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 2: Slow snapshot getter times out and returns 503 quickly
# ---------------------------------------------------------------------------

_TIMEOUT_S = 2.0  # must match SNAPSHOT_TIMEOUT_S in trend_port.py
_SLOW_SLEEP = _TIMEOUT_S + 3.0  # sleep well past the timeout
_FAST_DEADLINE = _TIMEOUT_S + 1.5  # the request must finish within this
_SLOW_RELEASE = threading.Event()
_SLOW_FINISHED = threading.Event()


def _slow_trends_get_snapshot(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
    """Simulates a hung DB connect by sleeping past the matching timeout."""
    assert strict is True
    _SLOW_RELEASE.wait(timeout=_SLOW_SLEEP)
    _SLOW_FINISHED.set()


def test_slow_snapshot_returns_503_quickly(client: TestClient, strict_matching: None) -> None:
    """A snapshot getter that sleeps past the timeout must cause a 503 within
    SNAPSHOT_TIMEOUT_S + a small buffer, not hang the server.
    """
    _SLOW_RELEASE.clear()
    _SLOW_FINISHED.clear()
    with patch(
        "app.features.trends.service.get_snapshot",
        side_effect=_slow_trends_get_snapshot,
    ):
        t0 = time.monotonic()
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})
        elapsed = time.monotonic() - t0

    _SLOW_RELEASE.set()
    assert _SLOW_FINISHED.wait(timeout=1)
    from app.features.matching import trend_port

    assert trend_port._WORKER_SLOT.acquire(timeout=1)
    trend_port._WORKER_SLOT.release()

    assert resp.status_code == 503, f"Expected 503 on timeout, got {resp.status_code}: {resp.text}"
    assert elapsed < _FAST_DEADLINE, (
        f"Request took {elapsed:.2f}s — should have timed out in ~{_TIMEOUT_S}s"
    )
    body = resp.json()
    assert body["error"]["code"] == "trend_unavailable"


# ---------------------------------------------------------------------------
# Test 3: 30 concurrent requests with a fake getter all complete
# ---------------------------------------------------------------------------

_CONCURRENCY = 30


def test_concurrent_match_requests_complete(client: TestClient) -> None:
    """30 concurrent GET /matches with a fake getter must all complete successfully.

    Uses a thread pool to simulate concurrent load.  Verifies no thread starvation,
    no deadlock, and no unexpected errors.
    """
    results: list[int] = []
    lock = threading.Lock()

    def one_request() -> int:
        resp = client.get("/api/v1/matches", params={"scenario": "moderate"})
        with lock:
            results.append(resp.status_code)
        return resp.status_code

    with patch(_FETCH_PATCH, side_effect=_fake_fetch_good):
        with ThreadPoolExecutor(max_workers=_CONCURRENCY) as pool:
            futures = [pool.submit(one_request) for _ in range(_CONCURRENCY)]
            statuses = [f.result(timeout=10) for f in as_completed(futures)]

    assert len(statuses) == _CONCURRENCY, f"Expected {_CONCURRENCY} responses, got {len(statuses)}"
    non_200 = [s for s in statuses if s != 200]
    assert not non_200, f"Some requests failed: {non_200}"


@pytest.mark.parametrize(
    ("next_scenario", "next_date"),
    [
        ("fast", trends_mocks.AVAILABLE_MOCK_DATES[0]),
        ("moderate", trends_mocks.AVAILABLE_MOCK_DATES[-1]),
    ],
)
def test_different_snapshot_waits_for_running_read(next_scenario: str, next_date: date) -> None:
    """Distinct requests queue behind the sole worker instead of failing fast."""
    from app.features.matching import trend_port

    first_date = trends_mocks.AVAILABLE_MOCK_DATES[0]
    started = threading.Event()
    release = threading.Event()
    second_started = threading.Event()
    active = 0
    max_active = 0
    active_lock = threading.Lock()

    def controlled_getter(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        nonlocal active, max_active
        with active_lock:
            active += 1
            max_active = max(max_active, active)
        try:
            if scenario == "moderate" and snapshot_date == first_date:
                started.set()
                assert release.wait(timeout=2)
            return trends_mocks.snapshot(scenario, snapshot_date)
        finally:
            with active_lock:
                active -= 1

    def second_read() -> TrendSnapshotResponse:
        second_started.set()
        return trend_port._call_with_timeout(next_scenario, next_date)

    with patch("app.features.trends.service.get_snapshot", side_effect=controlled_getter):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(trend_port._call_with_timeout, "moderate", first_date)
            try:
                assert started.wait(timeout=1)
                second = pool.submit(second_read)
                assert second_started.wait(timeout=1)
                time.sleep(0.05)
                assert not second.done(), (
                    "distinct snapshot was rejected before the worker finished"
                )
            finally:
                release.set()

            assert first.result(timeout=2).meta.snapshot_date == first_date
            next_snapshot = second.result(timeout=2)

    assert next_snapshot.meta.snapshot_date == next_date
    assert next_snapshot.meta.scenario == next_scenario
    assert max_active == 1


def test_identical_requests_share_one_running_read() -> None:
    from app.features.matching import trend_port

    started = threading.Event()
    release = threading.Event()
    second_started = threading.Event()
    calls = 0

    def controlled_getter(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        nonlocal calls
        calls += 1
        started.set()
        assert release.wait(timeout=2)
        return trends_mocks.snapshot(scenario, snapshot_date)

    def second_read() -> TrendSnapshotResponse:
        second_started.set()
        return trend_port._call_with_timeout("moderate")

    with patch("app.features.trends.service.get_snapshot", side_effect=controlled_getter):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(trend_port._call_with_timeout, "moderate")
            try:
                assert started.wait(timeout=1)
                second = pool.submit(second_read)
                assert second_started.wait(timeout=1)
                time.sleep(0.05)
                assert not second.done()
            finally:
                release.set()

            first_snapshot = first.result(timeout=2)
            second_snapshot = second.result(timeout=2)

    assert first_snapshot is second_snapshot
    assert calls == 1


def test_waiters_for_same_next_snapshot_share_one_read() -> None:
    from app.features.matching import trend_port

    first_started = threading.Event()
    release_first = threading.Event()
    next_started = threading.Event()
    release_next = threading.Event()
    waiters_started = threading.Event()
    waiter_count = 0
    next_calls = 0
    count_lock = threading.Lock()

    def controlled_getter(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        nonlocal next_calls
        if scenario == "moderate":
            first_started.set()
            assert release_first.wait(timeout=2)
        else:
            with count_lock:
                next_calls += 1
            next_started.set()
            assert release_next.wait(timeout=2)
        return trends_mocks.snapshot(scenario, snapshot_date)

    def queued_read() -> TrendSnapshotResponse:
        nonlocal waiter_count
        with count_lock:
            waiter_count += 1
            if waiter_count == 20:
                waiters_started.set()
        return trend_port._call_with_timeout("fast")

    with patch("app.features.trends.service.get_snapshot", side_effect=controlled_getter):
        with ThreadPoolExecutor(max_workers=21) as pool:
            first = pool.submit(trend_port._call_with_timeout, "moderate")
            try:
                assert first_started.wait(timeout=1)
                waiters = [pool.submit(queued_read) for _ in range(20)]
                assert waiters_started.wait(timeout=1)
                time.sleep(0.05)
                release_first.set()
                assert next_started.wait(timeout=1)
                time.sleep(0.05)
            finally:
                release_first.set()
                release_next.set()

            first.result(timeout=2)
            results = [future.result(timeout=2) for future in waiters]

    assert next_calls == 1
    assert all(result is results[0] for result in results)


def test_different_snapshot_wait_is_bounded() -> None:
    from app.features.matching import trend_port

    started = threading.Event()
    release = threading.Event()
    calls = 0

    def blocked_getter(snapshot_date: date | None, scenario: str) -> TrendSnapshotResponse:
        nonlocal calls
        calls += 1
        started.set()
        assert release.wait(timeout=2)
        return trends_mocks.snapshot(scenario, snapshot_date)

    with (
        patch("app.features.trends.service.get_snapshot", side_effect=blocked_getter),
        patch.object(trend_port, "WORKER_WAIT_S", 0.1),
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(trend_port._call_with_timeout, "moderate")
            try:
                assert started.wait(timeout=1)
                began = time.monotonic()
                with pytest.raises(trend_port.TrendUnavailable, match="still running"):
                    trend_port._call_with_timeout("fast")
                elapsed = time.monotonic() - began
                assert elapsed >= 0.08
                assert elapsed < 0.5
                assert calls == 1
            finally:
                release.set()
            first.result(timeout=2)


def test_timed_out_getter_does_not_spawn_more_workers(strict_matching: None) -> None:
    """A stuck getter occupies the sole slot until it really finishes."""
    from app.features.matching import trend_port

    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    calls = 0

    def blocked_getter(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        nonlocal calls
        assert strict is True
        calls += 1
        started.set()
        release.wait(timeout=2)
        finished.set()
        return None

    with (
        patch("app.features.trends.service.get_snapshot", side_effect=blocked_getter),
        patch.object(trend_port, "SNAPSHOT_TIMEOUT_S", 0.05),
        patch.object(trend_port, "WORKER_WAIT_S", 0.1),
    ):
        try:
            with pytest.raises(trend_port.TrendUnavailable, match="timed out"):
                trend_port._call_with_timeout("moderate")
            assert started.wait(timeout=1)

            started_followups = time.monotonic()
            with ThreadPoolExecutor(max_workers=30) as pool:
                followups = [
                    pool.submit(trend_port._call_with_timeout, "moderate") for _ in range(30)
                ]
                errors = [future.exception(timeout=1) for future in followups]
            followup_elapsed = time.monotonic() - started_followups

            assert all(isinstance(error, trend_port.TrendUnavailable) for error in errors)
            assert all("still running" in str(error) for error in errors)
            assert followup_elapsed < 0.5, f"Follow-up calls took {followup_elapsed:.3f}s"
            assert calls == 1
            active_workers = [
                thread for thread in threading.enumerate() if thread.name == "matching-m1-trends"
            ]
            assert len(active_workers) <= 1
        finally:
            release.set()

        assert finished.wait(timeout=1)
        assert trend_port._WORKER_SLOT.acquire(timeout=1)
        trend_port._WORKER_SLOT.release()


def test_m1_strict_timeout_maps_to_matching_503(client: TestClient, strict_matching: None) -> None:
    from app.features.trends import repository as trends_repository

    unavailable_error = trends_repository.TrendsUnavailableError

    def fail_closed(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        assert strict is True
        raise unavailable_error("database query timed out")

    with patch("app.features.trends.service.get_snapshot", side_effect=fail_closed):
        response = client.get("/api/v1/matches", params={"scenario": "moderate"})

    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "trend_unavailable"
