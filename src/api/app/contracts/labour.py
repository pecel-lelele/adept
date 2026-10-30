"""Observed national context, separate from role forecasts."""

from datetime import date

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta


class MalaysiaLabourContext(BaseModel):
    observed_month: date
    unemployment_rate: float = Field(ge=0, le=100)
    participation_rate: float = Field(ge=0, le=100)
    employment_population_ratio: float = Field(ge=0, le=100)
    meta: RecommendationMeta
