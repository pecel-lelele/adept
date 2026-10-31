"""Types shared by every feature, including the output contract rule (PROJECT_CONTEXT §11.8)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ScenarioId = Literal["moderate", "fast"]
RetrievalBasis = Literal["pipeline_fetch", "fetch_log", "git_commit_date", "unknown"]


class Source(BaseModel):
    name: str = Field(examples=["MOCK DATA"])
    url: str = Field(description="Empty only for mock data.")
    retrieved_at: date


class TrendSource(Source):
    retrieved_at_basis: RetrievalBasis = "unknown"
    retrieval_evidence: str | None = None


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


class VersionInfo(BaseModel):
    version: str
    revision: str | None
    dirty: bool | None
    environment: Literal["development", "production"]


class TrendProvenance(BaseModel):
    """Observation dates are independent of a snapshot's filing/label date.

    Null classification is unverified legacy provenance, never proof of live data.
    Retrieval is deliberately day precision, with evidence and its basis disclosed.
    """

    observation_window_start: date | None = None
    observation_window_end: date | None = None
    retrieved_at: date | None = None
    retrieved_at_basis: RetrievalBasis = "unknown"
    retrieval_evidence: str | None = None
    is_replay: bool | None = Field(default=None, strict=True)
    # Preserve existing clients while exposing explicit, unambiguous names.
    observed_from: date | None = None
    observed_to: date | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> "TrendProvenance":
        for canonical, legacy in (
            ("observation_window_start", "observed_from"),
            ("observation_window_end", "observed_to"),
        ):
            first, second = getattr(self, canonical), getattr(self, legacy)
            if first is not None and second is not None and first != second:
                raise ValueError("Conflicting observation windows")
            setattr(self, canonical, first or second)
            setattr(self, legacy, first or second)
        start, end = self.observation_window_start, self.observation_window_end
        if (start is None) != (end is None) or (start and end and start > end):
            raise ValueError("Observation window must contain ordered start and end dates")
        if self.is_replay is not None and (
            start is None
            or end is None
            or self.retrieved_at is None
            or self.retrieved_at_basis == "unknown"
            or not self.retrieval_evidence
        ):
            raise ValueError("Classified trend data requires observation and retrieval evidence")
        if self.is_replay is False and self.retrieved_at_basis == "git_commit_date":
            raise ValueError("A commit-date fallback cannot verify live ingestion")
        return self


class DataFreshness(TrendProvenance):
    snapshot_date: date = Field(
        description="Snapshot version/slot label; see observation_window_* for the measured period."
    )
    sources: list[TrendSource]
    is_mock: bool
    served_from: Literal["db", "fixture"]
    is_fallback: bool


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
