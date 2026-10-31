"""Guest preview reuses M1/M2 without persisting a profile or full ranking."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Form, UploadFile
from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.profile import CvExtractionResult, ExtractedSkill, SkillSuggestion
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.matching.repository import load_roles, role_label
from app.features.matching.scoring import MatchProfile, rank_roles
from app.features.matching.trend_port import fetch_snapshot
from app.features.profile.cv_parser import extract_pdf_bounded
from app.features.profile.router import check_cv_type, read_capped
from app.features.profile.service import extract_cv, skill_catalogue

router = APIRouter(prefix="/preview", tags=["preview"])


class TopRole(BaseModel):
    role_id: str
    label: str
    score: float
    trend_coverage: float


class SkillTrend(BaseModel):
    """How one extracted skill moves in the latest snapshot (free part of the preview)."""

    skill_id: str
    label: str
    direction: Literal["rising", "stable", "declining"]


class GuestPreview(BaseModel):
    skills: list[ExtractedSkill]
    unmatched_terms: list[str] = Field(default_factory=list, max_length=30)
    suggestions: list[SkillSuggestion] = []
    skill_trends: list[SkillTrend] = []
    top_role: TopRole | None
    other_role_count: int
    meta: RecommendationMeta
    truncated: bool
    requires_skill_confirmation: bool = True


class ConfirmedPreviewSkill(BaseModel):
    skill_id: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=1, le=5, strict=True)


class ConfirmedPreview(BaseModel):
    skills: list[ConfirmedPreviewSkill] = Field(min_length=1, max_length=200)
    scenario: ScenarioId = "moderate"


DIRECTION_BAND = 0.05  # same band as the trend pipeline


def _direction(v: float) -> Literal["rising", "stable", "declining"]:
    return "rising" if v > DIRECTION_BAND else "declining" if v < -DIRECTION_BAND else "stable"


def build_preview(
    filename: str,
    content: bytes,
    content_type: str,
    scenario: ScenarioId,
    *,
    include_suggestions: bool = True,
    extract_only: bool = False,
) -> GuestPreview:
    extraction = extract_cv(
        filename, content, content_type, include_suggestions=include_suggestions
    )
    if not extraction.skills or extract_only:
        return GuestPreview(
            skills=extraction.skills,
            unmatched_terms=extraction.unmatched_terms,
            suggestions=extraction.suggestions,
            top_role=None,
            other_role_count=0,
            meta=extraction.meta,
            truncated=extraction.truncated,
        )
    return rank_preview(extraction.skills, scenario, extraction=extraction)


def rank_preview(
    skills: list[ExtractedSkill],
    scenario: ScenarioId,
    *,
    extraction: CvExtractionResult | None = None,
    requires_skill_confirmation: bool = True,
) -> GuestPreview:
    """Score confirmed levels with the same catalogue matching engine as the app."""
    snap = fetch_snapshot(scenario)
    ranked = rank_roles(
        MatchProfile(skills={s.skill_id: float(s.level) for s in skills}),
        load_roles(),
        snap.velocities,
        reference_velocities=snap.reference_velocities,
    )
    top = ranked[0] if ranked else None
    trends = [
        SkillTrend(
            skill_id=s.skill_id, label=s.label, direction=_direction(snap.velocities[s.skill_id])
        )
        for s in skills
        if s.skill_id in snap.velocities
    ]
    return GuestPreview(
        skills=skills,
        unmatched_terms=extraction.unmatched_terms if extraction else [],
        suggestions=extraction.suggestions if extraction else [],
        skill_trends=trends,
        top_role=TopRole(
            role_id=top.role_id,
            label=role_label(top.role_id),
            score=top.score,
            trend_coverage=top.trend_coverage,
        )
        if top
        else None,
        other_role_count=max(0, len(ranked) - 1),
        meta=RecommendationMeta(
            sources=snap.sources,
            snapshot_date=snap.snapshot_date,
            scenario=scenario,
            is_estimate=True,
            served_from=snap.served_from,
            is_fallback=snap.is_fallback,
            observed_from=snap.observed_from,
            observed_to=snap.observed_to,
        ),
        truncated=extraction.truncated if extraction else False,
        requires_skill_confirmation=requires_skill_confirmation,
    )


@router.post("/cv")
async def preview_cv(
    file: UploadFile,
    synthetic_consent: Annotated[bool, Form()],
    scenario: ScenarioId = "moderate",
    include_suggestions: bool = True,
    extract_only: bool = False,
) -> GuestPreview:
    if not synthetic_consent:
        raise AppError(
            "Please agree that we may read your CV. It is read in memory and never stored.",
            status_code=422,
            code="consent_required",
        )
    content_type = check_cv_type(file.content_type, file.filename)
    content = await read_capped(file, get_settings().max_upload_bytes)
    if content_type == "application/pdf":
        content = (await asyncio.to_thread(extract_pdf_bounded, content)).encode("utf-8")
        content_type = "text/plain"
    return await asyncio.to_thread(
        build_preview,
        file.filename or "cv",
        content,
        content_type,
        scenario,
        include_suggestions=include_suggestions,
        extract_only=extract_only,
    )


@router.post("/cv/confirm")
def confirm_preview(data: ConfirmedPreview) -> GuestPreview:
    """Anonymous, stateless self-assessment; no CV, profile writes or model calls."""
    catalogue = {s.id: s.label for s in skill_catalogue().skills}
    ids = [s.skill_id for s in data.skills]
    if len(set(ids)) != len(ids) or any(skill_id not in catalogue for skill_id in ids):
        raise AppError("Choose distinct catalogue skills.", status_code=422, code="unknown_skill")
    # Confidence here denotes confirmed catalogue membership, not inferred proficiency.
    skills = [
        ExtractedSkill(
            skill_id=s.skill_id, label=catalogue[s.skill_id], level=s.level, confidence=1
        )
        for s in data.skills
    ]
    return rank_preview(skills, data.scenario, requires_skill_confirmation=False)
