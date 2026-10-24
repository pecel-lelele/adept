"""Single entry point for LLM calls: structured output, ID validation, logging.

Order of defences for every call:
1. Prompt text is PII-redacted and injection-filtered (`app.core.security`) to reduce
   contact-data exposure and instructions hidden in catalogue labels.
2. A circuit breaker fails fast after repeated provider failures.
3. The model may only return IDs from `candidates`; `validate_ids` raises on anything else.
4. Every call is recorded (provider, model, task, outcome) in a bounded in-memory log.

Features should call `select_ids_or_fallback`, which degrades to deterministic logic
whenever the model is unavailable or invents an ID.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from app.core.llm.provider import LLMProvider, LLMUnavailableError, get_provider
from app.core.llm.validator import UnknownIdError, validate_ids
from app.core.logging import get_logger
from app.core.security.pii import redact_text
from app.core.security.sanitize import clean_extracted_text

log = get_logger("app.llm")

Outcome = Literal["ok", "rejected_unknown_ids", "unavailable", "breaker_open"]

SYSTEM_PROMPT = (
    "Select only IDs from the catalogue. Never invent jobs, courses, SDG targets or "
    "statistics. Answer as JSON matching the schema."
)


class IdSelection(BaseModel):
    ids: list[str]
    rationale: str = ""


class LLMBusyError(LLMUnavailableError):
    """The circuit breaker is open; callers should use their fallback."""


@dataclass(frozen=True)
class LlmCallRecord:
    at: datetime
    provider: str
    model: str
    task: str
    n_candidates: int
    selected: tuple[str, ...]
    rejected: tuple[str, ...]
    outcome: Outcome


@dataclass
class CircuitBreaker:
    threshold: int = 3
    cooldown_s: float = 30.0
    failures: int = 0
    open_until: float = 0.0
    clock: Callable[[], float] = field(default=time.monotonic)

    def check(self) -> None:
        if self.clock() < self.open_until:
            raise LLMBusyError("LLM circuit breaker is open")

    def success(self) -> None:
        self.failures = 0

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = self.clock() + self.cooldown_s
            self.failures = 0
            log.warning("llm circuit breaker opened for %.0fs", self.cooldown_s)


CALL_LOG: deque[LlmCallRecord] = deque(maxlen=200)
BREAKER = CircuitBreaker()


def _record(provider: LLMProvider, task: str, n: int, outcome: Outcome, **ids: list[str]) -> None:
    rec = LlmCallRecord(
        at=datetime.now(UTC),
        provider=getattr(provider, "last_provider", provider.name),
        model=getattr(provider, "last_model", provider.model),
        task=task[:120],
        n_candidates=n,
        selected=tuple(ids.get("selected", [])),
        rejected=tuple(ids.get("rejected", [])),
        outcome=outcome,
    )
    CALL_LOG.append(rec)
    log.info(
        "llm.select_ids provider=%s model=%s task=%r outcome=%s ids=%s rejected=%s",
        rec.provider,
        rec.model,
        rec.task,
        outcome,
        list(rec.selected),
        list(rec.rejected),
    )


def build_prompt(task: str, candidates: Mapping[str, str]) -> str:
    safe = lambda text: redact_text(clean_extracted_text(text))  # noqa: E731
    catalogue = "\n".join(f"{cid}: {safe(label)}" for cid, label in candidates.items())
    return f"{safe(task)}\n\nCatalogue:\n{catalogue}"


def select_ids(
    task: str,
    candidates: Mapping[str, str],
    provider: LLMProvider | None = None,
    breaker: CircuitBreaker | None = None,
) -> IdSelection:
    """Ask the model to pick from `candidates` (id -> label); only known IDs survive."""
    provider = provider or get_provider()
    breaker = breaker or BREAKER
    try:
        breaker.check()
    except LLMBusyError:
        _record(provider, task, len(candidates), "breaker_open")
        raise
    try:
        result = provider.complete_structured(
            SYSTEM_PROMPT, build_prompt(task, candidates), IdSelection
        )
    except LLMUnavailableError:
        if provider.name != "none":
            breaker.failure()
        _record(provider, task, len(candidates), "unavailable")
        raise
    breaker.success()
    try:
        valid = validate_ids(result.ids, candidates.keys())
    except UnknownIdError as exc:
        _record(provider, task, len(candidates), "rejected_unknown_ids", rejected=exc.unknown)
        raise
    _record(provider, task, len(candidates), "ok", selected=valid)
    return IdSelection(ids=valid, rationale=redact_text(result.rationale))


def select_ids_or_fallback(
    task: str,
    candidates: Mapping[str, str],
    fallback: Callable[[], list[str]],
    provider: LLMProvider | None = None,
) -> tuple[list[str], bool]:
    """Return (ids, used_llm). Falls back to deterministic logic on any LLM problem."""
    try:
        return select_ids(task, candidates, provider).ids, True
    except (LLMUnavailableError, UnknownIdError):
        return fallback(), False
