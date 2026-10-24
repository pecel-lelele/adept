"""Shared rate limiting through PostgreSQL (M3_BACKEND=postgres).

Skipped unless ADEPT_TEST_DATABASE_URL points at a migrated database (CI runs it).
"""

import os
import uuid

import pytest

from app.core.security import rate_limit
from app.core.security.rate_limit import PostgresCounter

PG_URL = os.environ.get("ADEPT_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL, reason="ADEPT_TEST_DATABASE_URL not set")


def _client() -> str:
    return f"test-{uuid.uuid4().hex[:12]}"  # isolate from other runs


def test_two_api_instances_share_one_limit() -> None:
    clock = [1_000_040.0]  # 20 s into the window starting at 1_000_020
    a = PostgresCounter(PG_URL, {}, (4, 60), clock=lambda: clock[0])
    b = PostgresCounter(PG_URL, {}, (4, 60), clock=lambda: clock[0])
    ip = _client()
    results = [a.hit(ip, "/x")[0], b.hit(ip, "/x")[0], a.hit(ip, "/x")[0], b.hit(ip, "/x")[0]]
    assert results == [True, True, True, True]
    blocked = a.hit(ip, "/x")
    assert not blocked[0] and blocked[3] >= 1, "the 5th request is refused on either instance"
    assert not b.hit(ip, "/x")[0]


def test_previous_window_still_counts_partly() -> None:
    clock = [2_000_070.0]  # 30 s into the window starting at 2_000_040
    c = PostgresCounter(PG_URL, {}, (4, 60), clock=lambda: clock[0])
    ip = _client()
    for _ in range(4):
        assert c.hit(ip, "/x")[0]
    clock[0] = 2_000_110.0  # 10 s into the next window: 4 * (1 - 10/60) = 3.3 still counted
    assert c.hit(ip, "/x")[0] is False
    clock[0] = 2_000_155.0  # 55 s in: previous window weighs 4 * 5/60 = 0.3
    assert c.hit(ip, "/x")[0] is True


def test_unreachable_database_falls_back_to_memory() -> None:
    c = PostgresCounter("postgresql://nobody:x@127.0.0.1:1/none?connect_timeout=1", {}, (1, 60))
    ip = _client()
    assert c.hit(ip, "/x")[0] is True
    assert c.hit(ip, "/x")[0] is False, "still limited, by the in-memory fallback"


def test_pruning_keeps_the_previous_hourly_window() -> None:
    clock = [360_000_100.0]  # 100 s into an hourly window
    c = PostgresCounter(PG_URL, {}, (4, 3600), clock=lambda: clock[0])
    ip = _client()
    for _ in range(4):
        assert c.hit(ip, "/sync")[0]
    clock[0] = 360_003_610.0  # 10 s into the next hour: the last hour still weighs ~4
    c._hits = rate_limit._PRUNE_EVERY - 1  # the next hit prunes
    assert c.hit(ip, "/sync")[0] is False
    assert c.hit(ip, "/sync")[0] is False, "pruning must not forget the previous hour"
