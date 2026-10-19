"""F3 Scenarios & uncertainty (owner M1)."""

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId


class Scenario(BaseModel):
    id: ScenarioId
    label: str
    adoption_rate: float = Field(ge=0, le=1, description="Share of tasks adopting AI by horizon.")
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


class OutlookResponse(BaseModel):
    outlooks: list[RoleOutlook]
    meta: RecommendationMeta
