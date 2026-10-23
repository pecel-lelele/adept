"""Runpod primary, independently authenticated Gemini backup, grounded IDs and deadlines."""

import asyncio
import json
import time

import httpx
import pytest

from app.core.config import Settings
from app.core.llm.gateway import CALL_LOG, CircuitBreaker, select_ids
from app.core.llm.provider import (
    FailoverProvider,
    LLMUnavailableError,
    OpenAICompatibleProvider,
    build_provider,
    request_deadline,
)


def _provider(transport: httpx.MockTransport, timeout: float = 2) -> FailoverProvider:
    primary = OpenAICompatibleProvider(
        "runpod",
        "glm-5.3",
        "https://runpod.example/openai/v1",
        "runpod-test-key",
        transport=transport,
    )
    backup = OpenAICompatibleProvider(
        "gemini",
        "gemini-test",
        "https://gemini.example/openai",
        "gemini-test-key",
        transport=transport,
    )
    return FailoverProvider(primary, backup, timeout)


def _answer(content: str = '{"ids":["next"]}') -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_success_calls_only_runpod_with_low_reasoning_and_capped_output() -> None:
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer()

    provider = _provider(httpx.MockTransport(respond))
    assert select_ids("next", {"next": "Checked next step"}, provider, CircuitBreaker()).ids == [
        "next"
    ]
    assert len(seen) == 1 and seen[0].url.host == "runpod.example"
    body = json.loads(seen[0].content)
    assert body["model"] == "glm-5.3" and body["reasoning_effort"] == "low"
    assert body["max_tokens"] <= 1024
    assert (provider.last_provider, provider.last_model) == ("runpod", "glm-5.3")


def test_primary_error_uses_gemini_key_and_reports_actual_provider() -> None:
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.headers["authorization"]))
        return httpx.Response(429) if request.url.host == "runpod.example" else _answer()

    provider = _provider(httpx.MockTransport(respond))
    select_ids("next", {"next": "Checked next step"}, provider, CircuitBreaker())
    assert seen == [
        ("runpod.example", "Bearer runpod-test-key"),
        ("gemini.example", "Bearer gemini-test-key"),
    ]
    assert (CALL_LOG[-1].provider, CALL_LOG[-1].model) == ("gemini", "gemini-test")


def test_malformed_primary_json_can_use_backup() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return _answer("invalid json") if request.url.host == "runpod.example" else _answer()

    provider = _provider(httpx.MockTransport(respond))
    assert select_ids("next", {"next": "Checked next step"}, provider, CircuitBreaker()).ids
    assert provider.last_provider == "gemini"


def test_timeout_cancels_primary_and_leaves_time_for_backup() -> None:
    cancelled = []

    async def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "runpod.example":
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                cancelled.append(True)
                raise
        return _answer()

    provider = _provider(httpx.MockTransport(respond), timeout=0.3)
    started = time.monotonic()
    select_ids("next", {"next": "Checked next step"}, provider, CircuitBreaker())
    assert time.monotonic() - started < 0.8 and cancelled
    assert provider.last_provider == "gemini"


def test_expired_outer_deadline_starts_no_request() -> None:
    seen = []
    provider = _provider(httpx.MockTransport(lambda request: seen.append(request) or _answer()))
    with request_deadline(time.monotonic() - 1), pytest.raises(LLMUnavailableError):
        provider.chat([{"role": "user", "content": "test"}])
    assert not seen


def test_config_keeps_provider_keys_and_model_lists_on_their_own_endpoints() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="runpod",
        llm_model="glm-5.3",
        llm_base_url="https://runpod.example/openai/v1",
        runpod_api_key="runpod-test-key",
        gemini_api_key="gemini-test-key",
        llm_fallback_provider="gemini",
        llm_fallback_model="gemini-primary,gemini-backup",
    )
    provider = build_provider(settings)
    assert isinstance(provider, FailoverProvider)
    assert isinstance(provider.primary, OpenAICompatibleProvider)
    assert isinstance(provider.fallback, OpenAICompatibleProvider)
    assert provider.primary._fallbacks == ()
    assert provider.fallback.model == "gemini-primary"
    assert provider.fallback._fallbacks == ("gemini-backup",)
    assert provider.primary._headers["Authorization"] == "Bearer runpod-test-key"
    assert provider.fallback._headers["Authorization"] == "Bearer gemini-test-key"
