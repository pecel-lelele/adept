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


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    auth_mode: str
    database: Literal["ok", "unavailable"]


class DataFreshness(BaseModel):
    snapshot_date: date
    sources: list[Source]
    is_mock: bool


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
