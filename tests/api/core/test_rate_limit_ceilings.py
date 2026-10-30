"""Sign-up scarcity and the shared Adi ceiling (core/security/rate_limit.py)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security.rate_limit import (
    GLOBAL_LIMITS,
    ROUTE_LIMITS,
    RateLimitMiddleware,
    SlidingWindowCounter,
    global_bucket_for,
)

SECRET = "synthetic-proxy-secret"


def _visitor(n: int | str) -> dict[str, str]:
    """A distinct client address, signed the way the web proxy signs it."""
    return {"x-internal-proxy-secret": SECRET, "x-real-ip": f"192.0.2.{n}"}


def _app(**kwargs: object) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **kwargs)  # type: ignore[arg-type]

    @app.api_route("/api/v1/{path:path}", methods=["GET", "POST"])
    def anything(path: str) -> dict[str, str]:
        return {"path": path}

    return TestClient(app)


def test_signup_is_limited_more_tightly_than_login() -> None:
    signup, _ = ROUTE_LIMITS["/api/v1/auth/signup"]
    assert signup <= 5 < ROUTE_LIMITS["/api/v1/auth/login"][0]


def test_one_address_cannot_create_more_than_the_signup_allowance() -> None:
    client = _app()
    limit, _ = ROUTE_LIMITS["/api/v1/auth/signup"]
    codes = [client.post("/api/v1/auth/signup").status_code for _ in range(limit + 1)]
    assert codes == [200] * limit + [429]


def test_assistant_has_a_global_ceiling_above_the_per_account_limit() -> None:
    per_account, _ = ROUTE_LIMITS["/api/v1/assistant"]
    total, _ = GLOBAL_LIMITS["/api/v1/assistant"]
    assert per_account < total
    assert global_bucket_for("/api/v1/assistant/chat", GLOBAL_LIMITS) == "global:/api/v1/assistant"
    assert global_bucket_for("/api/v1/matches", GLOBAL_LIMITS) is None


def test_many_accounts_share_one_assistant_ceiling() -> None:
    client = _app(
        route_limits={"/api/v1/assistant": (2, 60)},
        global_limits={"/api/v1/assistant": (5, 60)},
        proxy_secret=SECRET,
    )
    codes = []
    for n in range(4):  # four fresh clients, each within its own allowance of 2
        for _ in range(2):
            codes.append(client.post("/api/v1/assistant/chat", headers=_visitor(n)).status_code)
    assert codes.count(200) == 5 and codes.count(429) == 3
    assert codes[:5] == [200] * 5
    # Other routes are unaffected by the assistant ceiling.
    assert client.get("/api/v1/matches").status_code == 200


def test_a_throttled_caller_does_not_consume_the_shared_ceiling() -> None:
    client = _app(
        route_limits={"/api/v1/assistant": (1, 60)},
        global_limits={"/api/v1/assistant": (2, 60)},
        proxy_secret=SECRET,
    )
    noisy = _visitor(1)
    assert client.post("/api/v1/assistant/chat", headers=noisy).status_code == 200
    for _ in range(5):
        assert client.post("/api/v1/assistant/chat", headers=noisy).status_code == 429
    quiet = _visitor(2)
    assert client.post("/api/v1/assistant/chat", headers=quiet).status_code == 200


def test_global_buckets_are_never_matched_by_a_request_path() -> None:
    counter = SlidingWindowCounter({"global:/api/v1/assistant": (1, 60)}, default=(100, 60))
    # Request paths start with "/", so they never select a "global:" bucket by prefix.
    assert counter.hit("ip", "/api/v1/assistant/chat", now=0)[1] == (100, 60)
    assert counter.hit("__global__", "/x", now=0, bucket="global:/api/v1/assistant")[0]
    assert not counter.hit("__global__", "/x", now=1, bucket="global:/api/v1/assistant")[0]
