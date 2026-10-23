"""F3 Scenarios & uncertainty (owner M1)."""

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId


class Scenario(BaseModel):
    id: ScenarioId
    label: str
    adoption_rate: float = Field(
        ge=0,
        le=1,
        description="Mean automation exposure of the tracked skills under this scenario.",
    )
    description: str


class ScenarioListResponse(BaseModel):
    scenarios: list[Scenario]
    meta: RecommendationMeta


class RoleOutlook(BaseModel):
    role_id: str
    scenario: ScenarioId
    outlook: float = Field(description="Projected demand index; 1.0 = current demand.")
    low: float
    high: float
    insufficient_evidence: bool = Field(
        default=False,
        description=(
            "True when skill coverage for this role is below MIN_COVERAGE_THRESHOLD "
            "(20%). The low/high range is still provided but should be treated with "
            "extra caution. Always an estimate."
        ),
    )


class OutlookResponse(BaseModel):
    outlooks: list[RoleOutlook]
    meta: RecommendationMeta
