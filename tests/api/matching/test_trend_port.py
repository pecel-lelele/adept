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


def test_different_snapshots_are_read_in_parallel() -> None:
    """Two users asking for different scenarios must not queue behind one another."""
    from app.features.matching import trend_port

    both_started = threading.Barrier(2, timeout=1)

    def getter(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        both_started.wait()  # only passes if the two reads run at the same time
        return trends_mocks.snapshot(scenario, trends_mocks.AVAILABLE_MOCK_DATES[-1])

    with patch("app.features.trends.service.get_snapshot", side_effect=getter):
        with ThreadPoolExecutor(max_workers=2) as pool:
            fast = pool.submit(trend_port._call_with_timeout, "fast")
            moderate = pool.submit(trend_port._call_with_timeout, "moderate")
            assert fast.result(timeout=3).meta.scenario == "fast"
            assert moderate.result(timeout=3).meta.scenario == "moderate"


def test_timed_out_read_does_not_block_other_requests(strict_matching: None) -> None:
    """A stuck read times out for its caller; the next caller is served normally."""
    from app.features.matching import trend_port

    release = threading.Event()
    good = trends_mocks.snapshot("moderate", trends_mocks.AVAILABLE_MOCK_DATES[-1])
    calls = 0

    def getter(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        nonlocal calls
        assert strict is True
        calls += 1
        if calls == 1:
            release.wait(timeout=2)
        return good

    with (
        patch("app.features.trends.service.get_snapshot", side_effect=getter),
        patch.object(trend_port, "SNAPSHOT_TIMEOUT_S", 0.05),
    ):
        try:
            with pytest.raises(trend_port.TrendUnavailable, match="timed out"):
                trend_port._call_with_timeout("moderate")
            started = time.monotonic()
            assert trend_port._call_with_timeout("moderate") is good
            assert time.monotonic() - started < 0.5
        finally:
            release.set()


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


def test_identical_reads_are_shared() -> None:
    """Many requests for the same snapshot start one database read."""
    from app.features.matching import trend_port

    calls = 0
    gate = threading.Event()
    good = trends_mocks.snapshot("moderate", trends_mocks.AVAILABLE_MOCK_DATES[-1])

    def getter(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        nonlocal calls
        calls += 1
        gate.wait(timeout=2)
        return good

    with patch("app.features.trends.service.get_snapshot", side_effect=getter):
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(trend_port._call_with_timeout, "moderate") for _ in range(10)]
            time.sleep(0.2)
            gate.set()
            assert all(f.result(timeout=3) is good for f in futures)
    assert calls == 1


def test_outstanding_reads_are_bounded(strict_matching: None) -> None:
    """When every slot holds a stuck read, new callers fail fast instead of queueing."""
    from app.features.matching import trend_port

    release = threading.Event()

    def stuck(snapshot_date, scenario, strict=False):  # noqa: ANN001,ARG001
        release.wait(timeout=3)

    with (
        patch("app.features.trends.service.get_snapshot", side_effect=stuck),
        patch.object(trend_port, "SNAPSHOT_TIMEOUT_S", 0.05),
        patch.object(trend_port, "_slots", threading.BoundedSemaphore(2)),
    ):
        try:
            for _ in range(2):  # each timed-out caller leaves its read holding a slot
                with pytest.raises(trend_port.TrendUnavailable, match="timed out"):
                    trend_port._call_with_timeout("moderate")
            started = time.monotonic()
            with pytest.raises(trend_port.TrendUnavailable, match="backed up"):
                trend_port._call_with_timeout("moderate")
            assert time.monotonic() - started < 0.2
        finally:
            release.set()
