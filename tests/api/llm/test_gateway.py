from typing import TypeVar

import pytest
from pydantic import BaseModel

from app.core.llm import (
    IdSelection,
    LLMUnavailableError,
    NullProvider,
    UnknownIdError,
    select_ids,
    validate_ids,
)

T = TypeVar("T", bound=BaseModel)


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    def complete_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        return schema.model_validate({"ids": self.ids, "rationale": "test"})


CANDIDATES = {"data-analyst": "Data Analyst", "rpa-developer": "RPA Developer"}


def test_validate_ids_dedupes_and_keeps_order() -> None:
    assert validate_ids(["b", "a", "b"], {"a", "b"}) == ["b", "a"]


def test_validate_ids_rejects_unknown() -> None:
    with pytest.raises(UnknownIdError) as exc:
        validate_ids(["a", "made-up"], {"a"})
    assert exc.value.unknown == ["made-up"]


def test_select_ids_passes_known_ids() -> None:
    result = select_ids("pick roles", CANDIDATES, FakeProvider(["data-analyst"]))
    assert result == IdSelection(ids=["data-analyst"], rationale="test")


def test_select_ids_rejects_invented_ids() -> None:
    with pytest.raises(UnknownIdError):
        select_ids("pick roles", CANDIDATES, FakeProvider(["prompt-wizard"]))


def test_null_provider_is_unavailable() -> None:
    with pytest.raises(LLMUnavailableError):
        select_ids("pick roles", CANDIDATES, NullProvider())
