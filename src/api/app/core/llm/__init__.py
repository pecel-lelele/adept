"""LLM gateway (F8, owner M3).

Rule: the model only *selects* IDs that already exist in the database. Every
selection goes through `validate_ids` before it reaches a user.
No provider is configured by default (LLM_PROVIDER=none); features fall back to
deterministic logic via `select_ids_or_fallback`.
"""

from app.core.llm.gateway import (
    CALL_LOG,
    CircuitBreaker,
    IdSelection,
    LLMBusyError,
    LlmCallRecord,
    build_prompt,
    select_ids,
    select_ids_or_fallback,
)
from app.core.llm.provider import (
    LLMProvider,
    LLMUnavailableError,
    NullProvider,
    disclosure,
    get_provider,
)
from app.core.llm.validator import UnknownIdError, validate_ids

__all__ = [
    "CALL_LOG",
    "CircuitBreaker",
    "IdSelection",
    "LLMBusyError",
    "LLMProvider",
    "LLMUnavailableError",
    "LlmCallRecord",
    "NullProvider",
    "UnknownIdError",
    "build_prompt",
    "disclosure",
    "get_provider",
    "select_ids",
    "select_ids_or_fallback",
    "validate_ids",
]
