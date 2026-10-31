"""The jobs Fetcher bounds one response by size and the whole run by a deadline."""

import time

import httpx
import pytest

from pipelines.jobs import sources


def _fetcher(body: bytes, deadline: float | None = None) -> sources.Fetcher:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(200, content=body, headers={"content-type": "application/json"})
                if r.url.path != "/robots.txt"
                else httpx.Response(404)
            )
        )
    )
    return sources.Fetcher(client=client, delay_s=0, deadline=deadline)


def test_json_is_read_through_the_stream() -> None:
    assert _fetcher(b'{"jobs": [1, 2]}').get_json("https://example.test/api") == {"jobs": [1, 2]}


def test_oversized_response_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "MAX_RESPONSE_BYTES", 10)
    with pytest.raises(ValueError, match="size limit"):
        _fetcher(b'{"jobs": []}' + b" " * 50).get_json("https://example.test/api")


def test_requests_stop_after_the_deadline() -> None:
    fetcher = _fetcher(b"{}", deadline=time.monotonic() - 1)
    with pytest.raises(sources.IncompleteRead):
        fetcher.get_json("https://example.test/api")


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_unavailable_or_denied_robots_never_authorizes_the_feed(status: int) -> None:
    seen = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(status)

    with httpx.Client(transport=httpx.MockTransport(answer)) as client:
        fetcher = sources.Fetcher(client=client, delay_s=0)
        with pytest.raises(PermissionError, match="robots"):
            fetcher.get_json("https://example.test/api")
    assert seen == ["/robots.txt"]


def test_html_error_page_is_not_a_robot_permission() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="<html>Service unavailable</html>")
        )
    ) as client:
        with pytest.raises(PermissionError, match="error page"):
            sources.Fetcher(client=client).get_json("https://example.test/api")
