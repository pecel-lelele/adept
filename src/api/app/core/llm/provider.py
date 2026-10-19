"""Provider interface. Implement one class per provider; pick it via LLM_PROVIDER."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str
    model: str

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        """Return the model's answer parsed into `schema` (structured output)."""
        ...


class NullProvider:
    """Default when no LLM is configured; callers must fall back to non-LLM logic."""

    name = "none"
    model = ""

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        raise LLMUnavailableError("No LLM provider configured (LLM_PROVIDER=none).")


def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "none":
        return NullProvider()
    raise LLMUnavailableError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
