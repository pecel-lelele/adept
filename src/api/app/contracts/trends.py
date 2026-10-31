"""F2 AI-trend signal layer + F3 Scenarios & uncertainty (owner M1).

This module contains two contract sets:
  - Legacy TrendSignal / RadarResponse / RoleTrendResponse (skeleton, kept for
    backward-compatibility with tests written against the old endpoints).
  - New TrendSnapshotResponse (the final patched contract, per the task spec).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, TrendProvenance, TrendSource

# ---------------------------------------------------------------------------
# Legacy contracts (skeleton – kept for backward compat with existing tests)
# ---------------------------------------------------------------------------

EntityType = Literal["role", "skill"]
Direction = Literal["rising", "stable", "declining"]


class TrendRecommendationMeta(RecommendationMeta, TrendProvenance):
    """Legacy trend endpoints retain the same explicit origin as snapshot/freshness."""

    sources: list[TrendSource] = Field(min_length=1)


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
    meta: TrendRecommendationMeta


class RoleTrendResponse(BaseModel):
    signal: TrendSignal
    meta: TrendRecommendationMeta


# ---------------------------------------------------------------------------
# New snapshot contracts (F2 final – TrendSnapshotResponse)
# See docs/skill-exposure-methodology.md for automation_exposure criteria.
# ---------------------------------------------------------------------------


class SourceRef(TrendSource):
    """Source retrieval basis is part of the trend response, not just its export."""


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


class TrendSnapshotMeta(TrendProvenance):
    sources: list[SourceRef]
    snapshot_date: date = Field(
        description="Snapshot version/slot label, not its observation or retrieval date."
    )
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


class TrendSnapshotResponse(BaseModel):
    meta: TrendSnapshotMeta
    items: list[SkillVelocity]


# ---------------------------------------------------------------------------
# Admin trend refresh (F2): dispatch the trends-refresh workflow, or re-score stored signals
# ---------------------------------------------------------------------------

RefreshRunStatus = Literal["queued", "in_progress", "completed"]


class TrendRefreshStatus(BaseModel):
    """State of the GitHub Actions trend refresh run (the workflow publishes the snapshot)."""

    status: RefreshRunStatus
    conclusion: str | None = Field(
        default=None, description="GitHub run conclusion once completed, e.g. success, failure."
    )
    run_id: int | None = Field(default=None, description="None until GitHub lists the new run.")
    run_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    dispatched: bool = Field(default=False, description="True when this request started the run.")
    already_running: bool = Field(
        default=False, description="True when an earlier run was still queued or in progress."
    )
    caches_cleared: bool = False
    snapshot_date: date | None = Field(
        default=None, description="Latest snapshot the app serves after a completed run."
    )
    served_from: Literal["db", "fixture"] | None = None
    is_fallback: bool = False


class TrendRescoreResult(BaseModel):
    """Outcome of re-scoring the latest stored signals (no ingest, no model call)."""

    status: Literal["published", "no_new_data", "failed"]
    message: str
    snapshot_date: date | None = Field(
        default=None, description="New snapshot date (published) or the one still live."
    )
    observed_from: date | None = None
    observed_to: date | None = None


class TrendSeriesPoint(BaseModel):
    day: date
    share: float | None = Field(
        description="Share of sampled arXiv papers in the 7 days ending on `day` that mention "
        "the skill; null when that window is not fully stored."
    )


class TrendSeriesLine(BaseModel):
    skill_id: str
    label: str
    points: list[TrendSeriesPoint]
    change: float | None = Field(description="Last minus first available share in the range.")


class TrendSeriesResponse(BaseModel):
    """Observed rolling shares per skill over a chosen date range (M1-018 paper store)."""

    start: date
    end: date
    window_days: int = 7
    available_from: date | None = Field(description="First day a full window is stored.")
    available_to: date | None = Field(description="Newest stored day.")
    lines: list[TrendSeriesLine]
    meta: RecommendationMeta


TrendEntityKind = Literal["skill", "role", "category"]
CompareMode = Literal["indexed", "raw"]
TrendRangePreset = Literal["1W", "1M", "3M", "6M"]


class TrendComparePoint(BaseModel):
    day: date
    value: float | None = Field(
        description="In the response's mode: rebased to 100 (indexed) or the raw share (0-1). "
        "Null when that day has no complete data; gaps are never interpolated."
    )


class TrendCompareOption(BaseModel):
    """A chartable entity from the reviewed taxonomy seeds."""

    entity: str = Field(description="`kind:id`, the form used in the URL and the `entities` query.")
    kind: TrendEntityKind
    label: str


class TrendCompareLine(BaseModel):
    entity: str
    kind: TrendEntityKind
    entity_id: str
    label: str
    points: list[TrendComparePoint]
    start_value: float | None = Field(description="First available value in the range.")
    end_value: float | None = Field(description="Last available value in the range.")
    change: float | None = Field(description="End minus start, in the response's mode.")
    moderate_end: float | None = Field(
        description="Moderate pace continuation at the horizon; an estimate, not a prediction."
    )
    fast_end: float | None = Field(
        description="Fast pace continuation at the horizon; an estimate, not a prediction."
    )
    projection: list[TrendComparePoint] = Field(
        description="The selected scenario's pace continuation after the last observed day."
    )


class TrendCompareResponse(BaseModel):
    """Skill, role and category lines over a stored date range, with a labelled projection.

    Skill lines are observed shares. Role and category lines are derived from arXiv skill
    signals, not observed role demand. `meta` covers the observed part; `projection_meta`
    covers the projected part and is always an estimate.
    """

    kind: TrendEntityKind
    start: date
    end: date
    window_days: int = 7
    step_days: int = Field(description="Days between points: 1, or 7 on long ranges.")
    available_from: date | None = Field(description="First day a full window is stored.")
    available_to: date | None = Field(description="Newest stored day.")
    mode: CompareMode
    raw_fallback: bool = Field(
        default=False,
        description="Rebasing was requested but no date has every line above 0, so raw is shown.",
    )
    base_date: date | None = Field(
        default=None, description="The date rebased to 100; null in raw mode."
    )
    horizon_days: int
    projected_from: date | None = Field(default=None, description="Last observed day.")
    projected_to: date | None = None
    lines: list[TrendCompareLine]
    options: list[TrendCompareOption]
    meta: RecommendationMeta
    projection_meta: RecommendationMeta | None = None
