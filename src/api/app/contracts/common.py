"""Types shared by every feature, including the output contract rule (PROJECT_CONTEXT §11.8)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

ScenarioId = Literal["moderate", "fast"]


class Source(BaseModel):
    name: str = Field(examples=["MOCK DATA"])
    url: str = Field(description="Empty only for mock data.")
    retrieved_at: date


class RecommendationMeta(BaseModel):
    """Attached to every response that contains a recommendation, score or trend."""

    sources: list[Source] = Field(min_length=1)
    snapshot_date: date
    scenario: ScenarioId
    is_estimate: bool = True
    served_from: Literal["db", "fixture"] | None = None
    is_fallback: bool = False
    observed_from: date | None = Field(
        default=None,
        description="Start of the period the source data measures; may predate snapshot_date.",
    )
    observed_to: date | None = Field(
        default=None, description="End of the period the source data measures."
    )


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    auth_mode: str
    database: Literal["ok", "unavailable"]


class DataFreshness(BaseModel):
    snapshot_date: date
    sources: list[Source]
    is_mock: bool
    served_from: Literal["db", "fixture"]
    is_fallback: bool


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


# Every mock response uses this source so mock data is never mistaken for real data.
MOCK_SOURCE = Source(name="MOCK DATA", url="", retrieved_at=date(2026, 10, 20))
MOCK_SNAPSHOT_DATE = date(2026, 10, 20)


def mock_meta(scenario: ScenarioId = "moderate", is_estimate: bool = True) -> RecommendationMeta:
    return RecommendationMeta(
        sources=[MOCK_SOURCE],
        snapshot_date=MOCK_SNAPSHOT_DATE,
        scenario=scenario,
        is_estimate=is_estimate,
    )


class OverviewSkill(BaseModel):
    skill_id: str
    label: str
    velocity: float = Field(description="Moderate-scenario velocity from the latest snapshot.")
    direction: Literal["rising", "declining", "stable"]


class OverviewRole(BaseModel):
    role_id: str
    label: str
    outlook: float = Field(description="Demand index under the moderate scenario (1 = today).")
    low: float
    high: float


class PlatformOverview(BaseModel):
    """Live figures for the public home page, computed from the same data the app uses."""

    skills_in_bank: int = Field(description="Skills a learner can pick (taxonomy).")
    skills_tracked: int = Field(description="Skills with a trend in the latest snapshot.")
    rising: int
    stable: int
    declining: int
    top_rising: list[OverviewSkill]
    top_declining: list[OverviewSkill]
    roles: int = Field(description="Future roles the matcher ranks.")
    top_roles: list[OverviewRole]
    courses: int
    free_courses: int
    hrd_claimable_courses: int
    providers: int
    sdg_goals_linked: int = Field(description="Distinct SDGs linked to at least one role.")
    meta: RecommendationMeta
