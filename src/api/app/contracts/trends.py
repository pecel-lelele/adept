"""F2 AI-trend signal layer + F3 Scenarios & uncertainty (owner M1).

This module contains two contract sets:
  - Legacy TrendSignal / RadarResponse / RoleTrendResponse (skeleton, kept for
    backward-compatibility with tests written against the old endpoints).
  - New TrendSnapshotResponse (the final patched contract, per the task spec).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta

# ---------------------------------------------------------------------------
# Legacy contracts (skeleton – kept for backward compat with existing tests)
# ---------------------------------------------------------------------------

EntityType = Literal["role", "skill"]
Direction = Literal["rising", "stable", "declining"]


class TrendSignal(BaseModel):
    entity_type: EntityType
    entity_id: str
    label: str
    direction: Direction
    growth_rate: float = Field(description="Year-on-year change in demand, e.g. 0.12 = +12%.")
    ai_exposure: float = Field(ge=0, le=1)
    automation_share: float = Field(ge=0, le=1)
    augmentation_share: float = Field(ge=0, le=1)
    trend_coverage: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Roles only: share of the role's skill importance that has trend data.",
    )
    insufficient_evidence: bool = Field(
        default=False,
        description="Roles only: trend_coverage is below 0.5, so the direction is not reliable.",
    )


class RadarResponse(BaseModel):
    items: list[TrendSignal]
    meta: RecommendationMeta


class RoleTrendResponse(BaseModel):
    signal: TrendSignal
    meta: RecommendationMeta


# ---------------------------------------------------------------------------
# New snapshot contracts (F2 final – TrendSnapshotResponse)
# See docs/skill-exposure-methodology.md for automation_exposure criteria.
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    name: str
    url: str
    retrieved_at: date


class SkillVelocity(BaseModel):
    skill_id: str
    skill_label: str
    research_velocity: float = Field(
        ..., description="Log-ratio growth of arXiv mention frequency, t0->t1"
    )
    labor_decay: float = Field(
        ..., description="Annualized labor-baseline projected change, as a fraction"
    )
    labor_decay_source_note: str = Field(
        ...,
        description=(
            "Citation for labor_decay, e.g. 'BLS 2023-2033 projection "
            "for SOC 43-3031 (Bookkeeping Clerks), -5.4%/yr'"
        ),
    )
    automation_exposure: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Curated editorial exposure coefficient, "
            "criteria published in docs/skill-exposure-methodology.md"
        ),
    )
    velocity_moderate: float
    velocity_fast: float
    direction_moderate: Literal["rising", "declining", "stable"] = Field(
        ...,
        description="rising if velocity_moderate > 0.05, declining if < -0.05, else stable",
    )
    direction_fast: Literal["rising", "declining", "stable"] = Field(
        ...,
        description="rising if velocity_fast > 0.05, declining if < -0.05, else stable",
    )


class TrendSnapshotMeta(BaseModel):
    sources: list[SourceRef]
    snapshot_date: date
    scenario: Literal["moderate", "fast"]
    is_estimate: bool = True
    served_from: Literal["db", "fixture"] = "db"
    is_fallback: bool = False
    weights: dict[str, float]
    labor_decay_is_static: bool = Field(
        default=True,
        description=(
            "If true, labor_decay does not change between snapshots "
            "unless manually refreshed; diffing logic should only "
            "compare velocity_moderate/velocity_fast between snapshots."
        ),
    )
    available_snapshots: list[date]
    data_provenance_note: str | None = Field(
        default=None,
        description=(
            "Optional explanation of data provenance, e.g. for historical "
            "arXiv date-window pulls or demo calibration."
        ),
    )
    observed_from: date | None = Field(
        default=None,
        description="Start of the period the source data measures; may predate snapshot_date.",
    )
    observed_to: date | None = Field(
        default=None, description="End of the period the source data measures."
    )


class TrendSnapshotResponse(BaseModel):
    meta: TrendSnapshotMeta
    items: list[SkillVelocity]
