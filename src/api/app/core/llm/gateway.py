"""Single entry point for LLM calls: structured output, ID validation, logging."""

from collections.abc import Mapping

from pydantic import BaseModel

from app.core.llm.provider import LLMProvider, get_provider
from app.core.llm.validator import validate_ids
from app.core.logging import get_logger

log = get_logger("app.llm")


class IdSelection(BaseModel):
    ids: list[str]
    rationale: str = ""


def select_ids(
    task: str,
    candidates: Mapping[str, str],
    provider: LLMProvider | None = None,
) -> IdSelection:
    """Ask the model to pick from `candidates` (id -> label); only known IDs survive."""
    provider = provider or get_provider()
    catalogue = "\n".join(f"{cid}: {label}" for cid, label in candidates.items())
    system = (
        "Select only IDs from the catalogue. Never invent jobs, courses, SDG targets or "
        "statistics. Answer as JSON matching the schema."
    )
    prompt = f"{task}\n\nCatalogue:\n{catalogue}"
    result = provider.complete_structured(system, prompt, IdSelection)
    valid = validate_ids(result.ids, candidates.keys())
    log.info(
        "llm.select_ids provider=%s model=%s task=%r ids=%s",
        provider.name,
        provider.model,
        task,
        valid,
    )
    return IdSelection(ids=valid, rationale=result.rationale)
