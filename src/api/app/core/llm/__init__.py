"""LLM gateway (F8, owner M3).

Rule: the model only *selects* IDs that already exist in the database. Every
selection goes through `validate_ids` before it reaches a user.
No provider is configured in the skeleton (LLM_PROVIDER=none).
"""

from app.core.llm.gateway import IdSelection, select_ids
from app.core.llm.provider import LLMProvider, LLMUnavailableError, NullProvider, get_provider
from app.core.llm.validator import UnknownIdError, validate_ids

__all__ = [
    "IdSelection",
    "LLMProvider",
    "LLMUnavailableError",
    "NullProvider",
    "UnknownIdError",
    "get_provider",
    "select_ids",
    "validate_ids",
]
