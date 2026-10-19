"""F8 Guardrails & transparency (owner M3)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

SourceKind = Literal["live_api", "verified_page", "curated", "synthetic", "mock"]


class Disclosure(BaseModel):
    llm_enabled: bool
    provider: str = Field(description="Configured LLM provider ('none' = no model is used).")
    model: str
    purpose: list[str]
    rules: list[str]
    calls_logged: int = Field(ge=0)
    rejected_ids: int = Field(ge=0, description="IDs the model returned that we rejected.")


class DataSourceInfo(BaseModel):
    name: str
    url: str
    retrieved_at: date
    kind: SourceKind
    used_for: str
    records: int = Field(ge=0)


class SourcesResponse(BaseModel):
    sources: list[DataSourceInfo]


class CounterfactualResult(BaseModel):
    name: str
    passed: bool
    detail: str


class FairnessReport(BaseModel):
    protected_attributes: list[str]
    api_inputs_checked: int = Field(ge=0)
    protected_inputs_found: list[str]
    counterfactual_checks: list[CounterfactualResult]
    passed: bool
