"""Sliding-window rate limiter per (client IP, route bucket). Adapted from KerjaCerdas.

Design (kept from KerjaCerdas `api/middleware/rate_limiter.py`):

- Counters are keyed by ``(ip, bucket)``, where *bucket* is the matched route prefix or
  ``__default__``. Keying by raw path would give every URL its own allowance and let an
  attacker grow the map without bound.
- The map is capped (``max_keys``) with LRU eviction that prefers expired windows and never
  drops a counter that is currently at its limit (eviction must not reset a throttle).
- ``X-Real-IP`` is trusted only when the request also carries the shared proxy secret, so a
  client cannot rotate a spoofed header to dodge the limit.

Simplified for Adept: the check-and-append runs without an ``await`` in between, so it is
atomic on the event loop and needs no per-key locks. Counters are per process: with N API
instances the effective limit is N times higher.
"""

from __future__ import annotations

import hmac
import time
from collections import OrderedDict, deque
from collections.abc import Mapping

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logging import get_logger

log = get_logger("app.security.rate_limit")

Limit = tuple[int, int]  # (max_requests, window_seconds)

DEFAULT_BUCKET = "__default__"

# Tighter buckets for routes that are expensive or write state.
ROUTE_LIMITS: dict[str, Limit] = {
    "/api/v1/profile/cv": (10, 60),  # upload + parsing
    "/api/v1/pathway/progress": (60, 60),  # writes
    "/api/v1/pathway/plans": (30, 60),  # writes + rebuilds a plan
    "/api/v1/guardrails": (60, 60),
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

    def _evict_one(self, now: float) -> None:
        for key in list(self._windows):  # LRU first
            if not self._live(key, now):
                del self._windows[key]
                return
        for key in list(self._windows):
            if not self._is_throttled(key, now):
                del self._windows[key]
                return
        log.warning("rate limiter full (%d keys), all throttled; evicting LRU", len(self))
        self._windows.popitem(last=False)

    def hit(self, ip: str, path: str, now: float | None = None) -> tuple[bool, Limit, int, int]:
        """Record one request. Returns (allowed, limit, remaining, retry_after_s)."""
        now = time.monotonic() if now is None else now
        bucket, limit = bucket_for(path, self.route_limits, self.default)
        key = (ip, bucket)
        if key in self._windows:
            self._windows.move_to_end(key)
        else:
            if len(self._windows) >= self.max_keys:
                self._evict_one(now)
            self._windows[key] = deque()
        dq = self._live(key, now)
        max_req, window = limit
        if len(dq) >= max_req:
            retry_after = int(window - (now - dq[0])) + 1
            return False, limit, 0, retry_after
        dq.append(now)
        return True, limit, max_req - len(dq), 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        default: Limit = (600, 60),
        route_limits: Mapping[str, Limit] | None = None,
        proxy_secret: str = "",
        max_keys: int = 10_000,
    ) -> None:
        super().__init__(app)
        self.counter = SlidingWindowCounter(
            ROUTE_LIMITS if route_limits is None else route_limits, default, max_keys
        )
        self.proxy_secret = proxy_secret

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = client_ip(request, self.proxy_secret)
        allowed, (max_req, window), remaining, retry_after = self.counter.hit(ip, request.url.path)
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
