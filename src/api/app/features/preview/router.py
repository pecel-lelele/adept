"""Guest preview reuses M1/M2 without persisting a profile or full ranking."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Form, UploadFile
from pydantic import BaseModel

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.profile import ExtractedSkill
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.matching.repository import load_roles
from app.features.matching.scoring import MatchProfile, rank_roles
from app.features.matching.trend_port import fetch_snapshot
from app.features.profile.router import read_capped
from app.features.profile.service import extract_cv

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
    skill_trends: list[SkillTrend] = []
    top_role: TopRole | None
    other_role_count: int
    meta: RecommendationMeta
    truncated: bool
    requires_skill_confirmation: Literal[True] = True


DIRECTION_BAND = 0.05  # same band as the trend pipeline


def _direction(v: float) -> Literal["rising", "stable", "declining"]:
    return "rising" if v > DIRECTION_BAND else "declining" if v < -DIRECTION_BAND else "stable"


def build_preview(
    filename: str, content: bytes, content_type: str, scenario: ScenarioId
) -> GuestPreview:
    extraction = extract_cv(filename, content, content_type)
    if not extraction.skills:
        return GuestPreview(
            skills=[],
            top_role=None,
            other_role_count=0,
            meta=extraction.meta,
            truncated=extraction.truncated,
        )
    snap = fetch_snapshot(scenario)
    ranked = rank_roles(
        MatchProfile(skills={s.skill_id: float(s.level) for s in extraction.skills}),
        load_roles(),
        snap.velocities,
    )
    path = Path(__file__).resolve().parents[4] / "data/seed/taxonomy/roles.csv"
    with path.open(encoding="utf-8") as handle:
        labels = {row["id"]: row["label"] for row in csv.DictReader(handle)}
    top = ranked[0] if ranked else None
    trends = [
        SkillTrend(
            skill_id=s.skill_id, label=s.label, direction=_direction(snap.velocities[s.skill_id])
        )
        for s in extraction.skills
        if s.skill_id in snap.velocities
    ]
    return GuestPreview(
        skills=extraction.skills,
        skill_trends=trends,
        top_role=TopRole(
            role_id=top.role_id,
            label=labels[top.role_id],
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
        ),
        truncated=extraction.truncated,
    )


@router.post("/cv")
async def preview_cv(
    file: UploadFile,
    synthetic_consent: Annotated[bool, Form()],
    scenario: ScenarioId = "moderate",
) -> GuestPreview:
    if not synthetic_consent:
        raise AppError(
            "Please agree that we may read your CV (it is not stored).",
            status_code=422,
            code="consent_required",
        )
    content_type = (file.content_type or "").split(";")[0].lower().strip()
    if content_type not in {"application/pdf", "text/plain"}:
        raise AppError("Use PDF or plain text.", status_code=415, code="unsupported_media_type")
    content = await read_capped(file, get_settings().max_upload_bytes)
    return await asyncio.to_thread(
        build_preview,
        file.filename or "cv",
        content,
        content_type,
        scenario,
    )
