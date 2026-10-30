"""F8 impact evidence: system measurements computed live on synthetic personas."""

import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.labour import MalaysiaLabourContext


class PathwayImpact(BaseModel):
    """One persona's pathway towards their top-ranked role in one scenario."""

    scenario: ScenarioId
    top_role_id: str
    top_role_label: str
    course_count: int = Field(ge=0)
    total_hours: float = Field(ge=0)
    free_course_share: float = Field(ge=0, le=1, description="Courses with cost_myr == 0.")
    free_hours_share: float = Field(ge=0, le=1)
    hrd_course_share: float = Field(ge=0, le=1, description="Courses flagged HRD Corp claimable.")
    hrd_hours_share: float = Field(ge=0, le=1)
    sdg_target_count: int = Field(ge=0, description="Distinct SDG targets the path contributes to.")
    sdg_targets: list[str] = Field(default_factory=list)


class PersonaImpact(BaseModel):
    persona_id: str
    source: str
    skill_count: int = Field(ge=0)
    hours_per_week: float = Field(ge=0)
    hrd_eligible: bool
    moderate: PathwayImpact
    fast: PathwayImpact
    top5_changed: int = Field(
        ge=0, le=5, description="Roles in the Moderate top 5 that are absent from the Fast top 5."
    )
    top_role_changed: bool


class ImpactAggregate(BaseModel):
    scenario: ScenarioId
    persona_count: int = Field(ge=0)
    median_free_course_share: float
    median_free_hours_share: float
    median_hrd_course_share: float
    median_total_hours: float
    median_sdg_target_count: float
    median_top5_changed: float


class CountBucket(BaseModel):
    key: str
    count: int = Field(ge=0)


class CatalogueCoverage(BaseModel):
    course_count: int = Field(ge=0)
    role_count: int = Field(ge=0)
    target_role_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)
    free_course_count: int = Field(ge=0)
    free_course_share: float = Field(ge=0, le=1)
    free_hours: float = Field(ge=0)
    sdg_target_count: int = Field(ge=0)
    role_sdg_link_count: int = Field(ge=0)
    by_language: list[CountBucket]
    by_provider_type: list[CountBucket]
    verified_recent_share: float = Field(ge=0, le=1)
    verified_window_days: int
    verified_since: date
    as_of: date = Field(description="Newest stored course verification date; not the clock.")


class FairnessEvidence(BaseModel):
    variants_tested: int = Field(ge=0)
    personas_tested: int = Field(ge=0)
    max_rank_change: int = Field(ge=0, description="Largest role-position change across swaps.")
    guardrail_report_passed: bool
    api_inputs_checked: int = Field(ge=0)
    protected_inputs_found: list[str]
    method: str


class EvidenceItem(BaseModel):
    """A figure quoted from a public page that was fetched and checked, with its source."""

    id: str
    figure: str = Field(min_length=1)
    value: float
    unit: str
    scope: str
    claim: str = Field(min_length=1)
    quote: str = Field(min_length=1, description="Short verbatim phrase from the page.")
    publisher: str = Field(min_length=1)
    title: str
    url: str = Field(min_length=1)
    retrieved_at: date
    published_at: date | None = None
    feature: str = Field(description="Key of the Adept feature that addresses it.")

    @model_validator(mode="after")
    def figure_matches_support(self) -> "EvidenceItem":
        def numbers(text: str) -> set[Decimal]:
            return {
                Decimal(part.replace(",", "")) for part in re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)
            }

        figure = numbers(self.figure)
        if len(figure) != 1 or Decimal(str(self.value)) not in figure:
            raise ValueError("Evidence value must match its displayed figure")
        if not figure <= numbers(self.quote + " " + self.claim):
            raise ValueError("Evidence figure must occur in its quotation or claim")
        if self.published_at and self.published_at > self.retrieved_at:
            raise ValueError("Publication cannot follow retrieval")
        return self


class ImpactSummary(BaseModel):
    personas: list[PersonaImpact]
    aggregates: list[ImpactAggregate]
    catalogue: CatalogueCoverage
    fairness: FairnessEvidence
    public_evidence: list[EvidenceItem]
    labour_context: MalaysiaLabourContext | None = Field(
        default=None, description="Stored DOSM labour force snapshot, with its real dates."
    )
    formulas: dict[str, str] = Field(description="How each displayed figure is derived.")
    persona_note: str
    meta: RecommendationMeta
