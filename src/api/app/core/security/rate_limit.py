"""Sliding-window rate limiter per (client IP, route bucket). Adapted from KerjaCerdas.

Design (kept from KerjaCerdas `api/middleware/rate_limiter.py`):

- Counters are keyed by ``(ip, bucket)``, where *bucket* is the matched route prefix or
  ``__default__``. Keying by raw path would give every URL its own allowance and let an
  attacker grow the map without bound.
- The map is capped (``max_keys``) with LRU eviction that prefers expired windows and never
  drops a counter that is currently at its limit (eviction must not reset a throttle). If
  every stored counter is at its limit, new clients are refused (429) until a window expires.
- ``X-Real-IP`` is trusted only when the request also carries the shared proxy secret, so a
  client cannot rotate a spoofed header to dodge the limit.

Simplified for Adept: the check-and-append runs without an ``await`` in between, so it is
atomic on the event loop and needs no per-key locks.

Two backends:

- ``SlidingWindowCounter`` (memory): per process. With N API instances the effective limit
  would be N times higher, so it is only the default for local dev and tests.
- ``PostgresCounter`` (``M3_BACKEND=postgres``): one counter per (client, bucket, window) in
  the UNLOGGED table ``rate_limit_counters``, shared by every instance. It approximates a
  sliding window from the current and previous fixed windows
  (``previous * (1 - elapsed / window) + current``), updated in a single atomic upsert. If
  the database fails it degrades to the in-memory counter rather than blocking everyone.
"""

from __future__ import annotations

import asyncio
import hmac
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.db import check_pool_connection
from app.core.logging import get_logger

log = get_logger("app.security.rate_limit")

Limit = tuple[int, int]  # (max_requests, window_seconds)

DEFAULT_BUCKET = "__default__"

# Tighter buckets for routes that are expensive or write state.
ROUTE_LIMITS: dict[str, Limit] = {
    "/api/v1/preview/cv": (10, 60),  # anonymous parsing and ranking
    "/api/v1/auth/login": (20, 60),  # slows password guessing
    "/api/v1/auth/signup": (20, 60),
    "/api/v1/auth/me/delete": (5, 60),  # re-checks a password
    "/api/v1/org/join": (10, 60),  # slows join-code guessing
    "/api/v1/org/funding": (60, 60),
    "/api/v1/org/packages": (30, 60),  # may build up to 50 member plans
    "/api/v1/pathway/catalogue/sync": (5, 3600),  # calls external APIs
    "/api/v1/sdg/sync": (5, 3600),
    "/api/v1/profile/cv": (10, 60),  # upload + parsing
    "/api/v1/pathway/progress/evidence": (20, 60),  # checks an external link
    "/api/v1/pathway/progress": (60, 60),  # writes
    "/api/v1/pathway/plans": (30, 60),  # writes + rebuilds a plan
    "/api/v1/guardrails": (60, 60),
    "/api/v1/assistant": (20, 60),  # each answer may call a paid language model
}


def client_ip(request: Request, proxy_secret: str) -> str:
    peer = request.client.host if request.client else "unknown"
    if proxy_secret:
        provided = request.headers.get("x-internal-proxy-secret", "")
        if hmac.compare_digest(provided, proxy_secret):
            forwarded = request.headers.get("x-real-ip", "").strip()
            if forwarded:
                return forwarded
    return peer


def bucket_for(path: str, route_limits: Mapping[str, Limit], default: Limit) -> tuple[str, Limit]:
    for prefix, limit in route_limits.items():
        if path.startswith(prefix):
            return prefix, limit
    return DEFAULT_BUCKET, default


class SlidingWindowCounter:
    """The limiter's state, separate from the middleware so it is easy to test."""

    def __init__(
        self,
        route_limits: Mapping[str, Limit],
        default: Limit,
        max_keys: int = 10_000,
    ) -> None:
        self.route_limits = dict(route_limits)
        self.default = default
        self.max_keys = max_keys
        self._windows: OrderedDict[tuple[str, str], deque[float]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._windows)

    def _limit_of(self, bucket: str) -> Limit:
        return self.route_limits.get(bucket, self.default)

    def _live(self, key: tuple[str, str], now: float) -> deque[float]:
        dq = self._windows[key]
        window = self._limit_of(key[1])[1]
        while dq and dq[0] < now - window:
            dq.popleft()
        return dq

    def _is_throttled(self, key: tuple[str, str], now: float) -> bool:
        return len(self._live(key, now)) >= self._limit_of(key[1])[0]

    def _evict_one(self, now: float) -> bool:
        """Drop one counter that costs nothing to lose. False if every counter is throttled.

        An active throttle is never dropped: recreating it empty would hand that client a
        fresh allowance.
        """
        for key in list(self._windows):  # LRU first
            if not self._live(key, now):
                del self._windows[key]
                return True
        for key in list(self._windows):
            if not self._is_throttled(key, now):
                del self._windows[key]
                return True
        return False

    def hit(self, ip: str, path: str, now: float | None = None) -> tuple[bool, Limit, int, int]:
        """Record one request. Returns (allowed, limit, remaining, retry_after_s)."""
        now = time.monotonic() if now is None else now
        bucket, limit = bucket_for(path, self.route_limits, self.default)
        key = (ip, bucket)
        if key in self._windows:
            self._windows.move_to_end(key)
        else:
            if len(self._windows) >= self.max_keys and not self._evict_one(now):
                # Map full of active throttles: refuse newcomers until a window expires,
                # rather than forget a block.
                log.warning("rate limiter full (%d keys), all throttled; rejecting", len(self))
                return False, limit, 0, limit[1]
            self._windows[key] = deque()
        dq = self._live(key, now)
        max_req, window = limit
        if len(dq) >= max_req:
            retry_after = int(window - (now - dq[0])) + 1
            return False, limit, 0, retry_after
        dq.append(now)
        return True, limit, max_req - len(dq), 0


Hit = tuple[bool, Limit, int, int]  # (allowed, limit, remaining, retry_after_s)

_UPSERT = """
WITH up AS (
    INSERT INTO rate_limit_counters (client, bucket, window_start, hits)
    VALUES (%(client)s, %(bucket)s, %(current)s, 1)
    ON CONFLICT (client, bucket, window_start)
    DO UPDATE SET hits = rate_limit_counters.hits + 1
    RETURNING hits
)
SELECT up.hits, COALESCE((
    SELECT hits FROM rate_limit_counters
    WHERE client = %(client)s AND bucket = %(bucket)s AND window_start = %(previous)s
), 0) FROM up
"""
_PRUNE = "DELETE FROM rate_limit_counters WHERE window_start < %s"
_PRUNE_EVERY = 1000


class PostgresCounter:
    """Rate-limit counters shared by every API instance through PostgreSQL."""

    def __init__(
        self,
        conninfo: str,
        route_limits: Mapping[str, Limit],
        default: Limit,
        fallback: SlidingWindowCounter | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.route_limits = dict(route_limits)
        self.default = default
        self.fallback = (
            fallback if fallback is not None else SlidingWindowCounter(route_limits, default)
        )
        # hit() runs in worker threads, including its in-memory outage fallback.
        self._lock = threading.Lock()
        self.clock = clock
        self._hits = 0
        # The estimate reads the previous window too, so pruning keeps two of the longest windows.
        longest = max(window for _, window in [*self.route_limits.values(), default])
        self._keep_s = 2 * longest
        self.pool = ConnectionPool(
            conninfo,
            min_size=0,
            max_size=4,
            timeout=2.0,
            open=False,
            check=lambda conn: check_pool_connection(self.pool, conn),
            kwargs={
                "autocommit": True,
                "connect_timeout": 2,
                "options": "-c statement_timeout=2000 -c lock_timeout=1000",
            },
        )
        self._opened = False

    def _conn_pool(self) -> ConnectionPool:
        with self._lock:
            if not self._opened:
                self.pool.open(wait=False)
                self._opened = True
        return self.pool

    def hit(self, ip: str, path: str) -> Hit:
        bucket, limit = bucket_for(path, self.route_limits, self.default)
        max_req, window = limit
        now = self.clock()
        current = int(now // window) * window
        elapsed = now - current
        params = {"client": ip, "bucket": bucket, "current": current, "previous": current - window}
        try:
            with self._conn_pool().connection() as conn:
                row = conn.execute(_UPSERT, params).fetchone()
                with self._lock:
                    self._hits += 1
                    prune = self._hits % _PRUNE_EVERY == 0
                if prune:
                    conn.execute(_PRUNE, (int(now) - self._keep_s,))
        except (psycopg.Error, PoolTimeout) as exc:
            log.warning("shared rate limiter unavailable, using in-memory counter: %s", exc)
            with self._lock:
                return self.fallback.hit(ip, path)
        assert row is not None
        hits, previous = int(row[0]), int(row[1])
        estimate = previous * (1 - elapsed / window) + hits
        if estimate > max_req:
            return False, limit, 0, int(window - elapsed) + 1
        return True, limit, max(0, int(max_req - estimate)), 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        default: Limit = (600, 60),
        route_limits: Mapping[str, Limit] | None = None,
        proxy_secret: str = "",
        max_keys: int = 10_000,
        shared_conninfo: str = "",
    ) -> None:
        super().__init__(app)
        limits = ROUTE_LIMITS if route_limits is None else route_limits
        self.counter = SlidingWindowCounter(limits, default, max_keys)
        self.shared = (
            PostgresCounter(shared_conninfo, limits, default, fallback=self.counter)
            if shared_conninfo
            else None
        )
        self.proxy_secret = proxy_secret

    async def _hit(self, ip: str, path: str) -> Hit:
        if self.shared is not None:
            # Blocking database call: run it off the event loop.
            return await asyncio.to_thread(self.shared.hit, ip, path)
        return self.counter.hit(ip, path)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = client_ip(request, self.proxy_secret)
        allowed, (max_req, window), remaining, retry_after = await self._hit(ip, request.url.path)
        headers = {
            "X-RateLimit-Limit": str(max_req),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Window": str(window),
        }
        if not allowed:
            log.warning("rate limit exceeded ip=%s path=%s", ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests."}},
                headers={**headers, "Retry-After": str(retry_after)},
            )
        response = await call_next(request)
        response.headers.update(headers)
        return response
