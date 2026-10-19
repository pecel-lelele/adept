from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security.rate_limit import DEFAULT_BUCKET, RateLimitMiddleware, SlidingWindowCounter

LIMITS = {"/api/v1/profile/cv": (2, 60)}


def _app(**kwargs: object) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **kwargs)  # type: ignore[arg-type]

    @app.get("/api/v1/{path:path}")
    def anything(path: str) -> dict[str, str]:
        return {"path": path}

    return TestClient(app)


def test_counter_blocks_after_limit_and_recovers_after_window() -> None:
    c = SlidingWindowCounter(LIMITS, default=(3, 10))
    assert [c.hit("1.1.1.1", "/x", now=t)[0] for t in (0, 1, 2, 3)] == [True, True, True, False]
    assert c.hit("1.1.1.1", "/x", now=11)[0], "window slid, request allowed again"


def test_default_bucket_is_shared_across_paths() -> None:
    """Walking distinct URLs must not reset the allowance (KerjaCerdas finding)."""
    c = SlidingWindowCounter({}, default=(2, 60))
    assert c.hit("ip", "/api/v1/roles/a", now=0)[0]
    assert c.hit("ip", "/api/v1/roles/b", now=0)[0]
    assert not c.hit("ip", "/api/v1/roles/c", now=0)[0]
    assert len(c) == 1


def test_route_bucket_is_separate_from_default() -> None:
    c = SlidingWindowCounter(LIMITS, default=(100, 60))
    for _ in range(2):
        assert c.hit("ip", "/api/v1/profile/cv", now=0)[0]
    assert not c.hit("ip", "/api/v1/profile/cv", now=0)[0]
    assert c.hit("ip", "/api/v1/matches", now=0)[0]


def test_eviction_never_drops_a_throttled_counter() -> None:
    c = SlidingWindowCounter({}, default=(2, 60), max_keys=2)
    c.hit("attacker", "/", now=0)
    c.hit("attacker", "/", now=0)  # now throttled
    c.hit("b", "/", now=0)  # under its limit
    c.hit("c", "/", now=0)  # map full: must evict "b", not the attacker
    assert ("attacker", DEFAULT_BUCKET) in c._windows
    assert ("b", DEFAULT_BUCKET) not in c._windows
    assert not c.hit("attacker", "/", now=1)[0], "eviction must not reset a throttle"


def test_middleware_returns_429_with_retry_after() -> None:
    client = _app(default=(2, 60), route_limits={})
    assert client.get("/api/v1/a").status_code == 200
    resp = client.get("/api/v1/b")
    assert resp.headers["X-RateLimit-Remaining"] == "0"
    blocked = client.get("/api/v1/c")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_spoofed_real_ip_is_ignored_without_the_proxy_secret() -> None:
    client = _app(default=(1, 60), route_limits={}, proxy_secret="s3cret")
    assert client.get("/api/v1/a", headers={"X-Real-IP": "9.9.9.1"}).status_code == 200
    assert client.get("/api/v1/a", headers={"X-Real-IP": "9.9.9.2"}).status_code == 429


def test_real_ip_is_trusted_with_the_proxy_secret() -> None:
    client = _app(default=(1, 60), route_limits={}, proxy_secret="s3cret")
    for ip in ("9.9.9.1", "9.9.9.2"):
        headers = {"X-Real-IP": ip, "X-Internal-Proxy-Secret": "s3cret"}
        assert client.get("/api/v1/a", headers=headers).status_code == 200
