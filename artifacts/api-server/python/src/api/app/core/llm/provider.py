"""LLM providers. Pick one with LLM_PROVIDER; every provider is disclosed on /about.

- `none` (default): no model. Features use their deterministic logic.
- `replit`: Replit AI Integrations (billed to Replit credits). Replit injects an OpenAI-compatible
  base URL and key into apps that run on Replit; set LLM_BASE_URL / LLM_API_KEY to override.
- `gemini`: Google AI Studio's OpenAI-compatible endpoint with an AI Studio key (LLM_API_KEY).
- `openai`, `openrouter`: their public OpenAI-compatible APIs with LLM_API_KEY.
- `runpod`: a Runpod public or Serverless endpoint, LLM_BASE_URL =
  https://api.runpod.ai/v2/<endpoint-id>/openai/v1 and RUNPOD_API_KEY = a Runpod API key.
- `openai_compatible`: any other server that speaks the Chat Completions API (LLM_BASE_URL).

All of them speak the same Chat Completions protocol, so one client serves every option.
LLM_FALLBACK_PROVIDER switches to a separately authenticated backup endpoint only after a
primary failure. Without it, LLM_FALLBACK_MODEL retains same-provider retry behaviour.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
_DEADLINE: ContextVar[float | None] = ContextVar("llm_deadline", default=None)


@contextmanager
def request_deadline(deadline: float | None) -> Iterator[None]:
    """Limit all provider attempts to the enclosing request's remaining time."""
    token = _DEADLINE.set(deadline)
    try:
        yield
    finally:
        _DEADLINE.reset(token)


ChatMessage = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class LLMUnavailableError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str
    model: str

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        """Return the model's answer parsed into `schema` (structured output)."""
        ...

    def chat(self, messages: list[ChatMessage], max_tokens: int = 600) -> str:
        """Return the model's text reply to a conversation."""
        ...


class NullProvider:
    """Default when no LLM is configured; callers must fall back to non-LLM logic."""

    name = "none"
    model = ""

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        raise LLMUnavailableError("No LLM provider configured (LLM_PROVIDER=none).")

    def chat(self, messages: list[ChatMessage], max_tokens: int = 600) -> str:
        raise LLMUnavailableError("No LLM provider configured (LLM_PROVIDER=none).")


# Base URLs of the public APIs; `replit` reads the URL Replit injects into the app.
_DEFAULT_BASE = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
# OpenAI's newer models take `max_completion_tokens` and only the default temperature;
# vLLM (Runpod) and OpenRouter accept the classic `max_tokens` with a temperature.
_OPENAI_STYLE = {"openai", "replit"}
# A model attempt needs at least this long to be worth starting.
MIN_ATTEMPT_S = 3.0


class OpenAICompatibleProvider:
    """Chat Completions over HTTPS with a hard timeout. Errors become LLMUnavailableError."""

    def __init__(
        self,
        name: str,
        model: str,
        base_url: str,
        api_key: str,
        timeout_s: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
        fallback_models: tuple[str, ...] = (),
    ) -> None:
        if not model:
            raise LLMUnavailableError(f"LLM_MODEL is required for LLM_PROVIDER={name}.")
        if not base_url:
            raise LLMUnavailableError(f"LLM_BASE_URL is required for LLM_PROVIDER={name}.")
        self.name = name
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        if name == "openrouter":
            self._headers["X-Title"] = "Adept"
        self._timeout = timeout_s
        self._transport = transport
        self._fallbacks = tuple(m for m in fallback_models if m and m != model)
        self._last_model: ContextVar[str] = ContextVar("llm_used_model", default=model)

    @property
    def last_model(self) -> str:
        """Model used in this caller's context, never another concurrent request's model."""
        return self._last_model.get()

    def _body(self, messages: list[ChatMessage], max_tokens: int, model: str) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model, "messages": messages}
        if self.name in _OPENAI_STYLE:
            body["max_completion_tokens"] = max_tokens
        else:
            body["max_tokens"] = max_tokens
            body["temperature"] = 0.3
        if self.name in {"gemini", "runpod"}:
            # Short, grounded answers: light thinking keeps latency and free-tier tokens low.
            body["reasoning_effort"] = "low"
        if self.name == "runpod":
            body["max_tokens"] = min(max_tokens, 1024)
        return body

    def _post(self, messages: list[ChatMessage], max_tokens: int) -> str:
        """Use cancellable async I/O under a single wall-clock deadline, including retries."""
        if self.name == "runpod" and not self._headers:
            raise LLMUnavailableError("Runpod API key is not configured.")
        self._last_model.set(self.model)
        deadline = time.monotonic() + self._timeout
        outer = _DEADLINE.get()
        if outer is not None:
            deadline = min(deadline, outer)
        try:
            text, model = asyncio.run(self._post_until(messages, max_tokens, deadline))
        except TimeoutError as exc:
            raise LLMUnavailableError(f"{self.name}: model deadline exceeded") from exc
        self._last_model.set(model)
        return text

    async def _post_until(
        self, messages: list[ChatMessage], max_tokens: int, deadline: float
    ) -> tuple[str, str]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LLMUnavailableError(f"{self.name}: request deadline exceeded")
        async with asyncio.timeout(remaining):
            return await self._attempts(messages, max_tokens, deadline)

    async def _attempts(
        self, messages: list[ChatMessage], max_tokens: int, deadline: float
    ) -> tuple[str, str]:
        last: LLMUnavailableError | None = None
        for index, model in enumerate((self.model, *self._fallbacks)):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or (index > 0 and remaining < MIN_ATTEMPT_S):
                break
            try:
                text = await self._post_once(self._body(messages, max_tokens, model), remaining)
            except LLMUnavailableError as exc:
                last = exc
                continue
            return text, model
        raise last or LLMUnavailableError(f"{self.name}: no time left for another model")

    async def _post_once(self, body: dict[str, Any], timeout_s: float) -> str:
        try:
            async with httpx.AsyncClient(timeout=timeout_s, transport=self._transport) as client:
                response = await client.post(self._url, headers=self._headers, json=body)
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"{self.name} request failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise LLMUnavailableError(
                f"{self.name} {body['model']} answered HTTP {response.status_code}"
            )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError(f"{self.name} returned an unexpected response") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMUnavailableError(f"{self.name} returned an empty answer")
        return content.strip()

    def chat(self, messages: list[ChatMessage], max_tokens: int = 600) -> str:
        return self._post(messages, max_tokens)

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        messages = [
            {
                "role": "system",
                "content": system
                + "\nReply with one JSON object only, matching this JSON schema:\n"
                + json.dumps(schema.model_json_schema()),
            },
            {"role": "user", "content": prompt},
        ]
        text = self._post(messages, 800)
        start, end = text.find("{"), text.rfind("}")
        try:
            return schema.model_validate_json(text[start : end + 1] if start >= 0 else text)
        except ValidationError as exc:
            raise LLMUnavailableError("The model's answer did not match the schema") from exc


def _replit_value(setting: str, env_name: str) -> str:
    return setting or os.environ.get(env_name, "")


class FailoverProvider:
    """Primary first; a separately authenticated fallback shares one request deadline.

    Reserve up to 40% of the budget (at most eight seconds) for the backup. Identity is
    request-local, so logging and the assistant cite the provider that actually answered.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider, timeout_s: float) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name, self.model = primary.name, primary.model
        self.timeout_s = timeout_s
        self._used: ContextVar[tuple[str, str]] = ContextVar(
            "llm_used_provider", default=(self.name, self.model)
        )

    @property
    def last_provider(self) -> str:
        return self._used.get()[0]

    @property
    def last_model(self) -> str:
        return self._used.get()[1]

    def _call(self, call: Callable[[LLMProvider], R]) -> R:
        now = time.monotonic()
        deadline = min(now + self.timeout_s, _DEADLINE.get() or float("inf"))
        reserve = min(8.0, max(0.0, deadline - now) * 0.4)
        for provider, until in (
            (self.primary, deadline - reserve),
            (self.fallback, deadline),
        ):
            if until <= time.monotonic():
                continue
            self._used.set((provider.name, provider.model))
            try:
                with request_deadline(until):
                    result = call(provider)
            except LLMUnavailableError:
                if provider is self.fallback:
                    raise
                continue
            self._used.set((provider.name, getattr(provider, "last_model", provider.model)))
            return result
        raise LLMUnavailableError("No time left for an LLM attempt")

    def chat(self, messages: list[ChatMessage], max_tokens: int = 600) -> str:
        return self._call(lambda provider: provider.chat(messages, max_tokens))

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        return self._call(lambda provider: provider.complete_structured(system, prompt, schema))


def build_provider(settings: Settings) -> LLMProvider:
    name = settings.llm_provider.strip().lower()
    if name in ("", "none"):
        return NullProvider()
    if name == "replit":
        base = _replit_value(settings.llm_base_url, "AI_INTEGRATIONS_OPENAI_BASE_URL")
        key = _replit_value(settings.llm_api_key, "AI_INTEGRATIONS_OPENAI_API_KEY")
    elif name in ("gemini", "openai", "openrouter", "runpod", "openai_compatible"):
        base = settings.llm_base_url or _DEFAULT_BASE.get(name, "")
        key = (
            settings.runpod_api_key
            if name == "runpod"
            else settings.gemini_api_key
            if name == "gemini"
            else ""
        ) or settings.llm_api_key
    else:
        raise LLMUnavailableError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    fallback_name = settings.llm_fallback_provider.strip().lower()
    models = tuple(m.strip() for m in settings.llm_fallback_model.split(",") if m.strip())
    primary = OpenAICompatibleProvider(
        name=name,
        model=settings.llm_model,
        base_url=base,
        api_key=key,
        timeout_s=settings.llm_timeout_s,
        fallback_models=() if fallback_name else models,
    )
    if not fallback_name:
        return primary
    if fallback_name not in _DEFAULT_BASE or not models:
        raise LLMUnavailableError("Configure a supported fallback provider and model.")
    fallback_key = settings.llm_fallback_api_key or (
        settings.gemini_api_key if fallback_name == "gemini" else ""
    )
    if not fallback_key:
        # Keep the primary usable when an optional backup key has not been supplied.
        return primary
    backup = OpenAICompatibleProvider(
        name=fallback_name,
        model=models[0],
        base_url=settings.llm_fallback_base_url or _DEFAULT_BASE[fallback_name],
        api_key=fallback_key,
        timeout_s=settings.llm_timeout_s,
        fallback_models=models[1:],
    )
    return FailoverProvider(primary, backup, settings.llm_timeout_s)


_cached: tuple[tuple[object, ...], LLMProvider] | None = None


def get_provider() -> LLMProvider:
    """The configured provider (built once per configuration)."""
    global _cached
    settings = get_settings()
    key = (
        settings.llm_provider,
        settings.llm_model + "|" + settings.llm_fallback_model,
        settings.llm_base_url,
        settings.llm_api_key,
        settings.runpod_api_key,
        settings.gemini_api_key,
        settings.llm_timeout_s,
        settings.llm_fallback_provider,
        settings.llm_fallback_base_url,
        settings.llm_fallback_api_key,
    )
    if _cached is None or _cached[0] != key:
        _cached = (key, build_provider(settings))
    return _cached[1]


def disclosure() -> tuple[str, str]:
    """(provider, model) as configured, for the About page and README disclosure.

    Read from settings, not hard-coded, so the disclosure cannot drift from what runs.
    """
    settings = get_settings()
    model = settings.llm_model
    if settings.llm_provider != "none" and settings.llm_fallback_model:
        backup = settings.llm_fallback_model
        if settings.llm_fallback_provider:
            backup = f"{settings.llm_fallback_provider} / {backup}"
        model += f" (fallback: {backup})"
    return settings.llm_provider, model
