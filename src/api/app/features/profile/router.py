"""Profile intake API router (F1).

Endpoints:
  POST   /profile/questionnaire  → M2-02 intake questionnaire
  GET    /profile/me             → current user profile
  POST   /profile                → upsert core profile fields (legacy)
  POST   /profile/cv             → M2-01 CV parsing pipeline
  PUT    /profile/skills         → M2-03 legacy skill replacement
  PUT    /profile/skills/confirm → M2-03 skill confirmation screen

All endpoints require authentication via the X-Demo-User header (demo mode)
or a Bearer token (Supabase mode). See app/core/auth.py.
"""

from fastapi import APIRouter, UploadFile

from app.contracts.profile import CvExtractionResult, Profile, ProfileIn, SkillsUpdate
from app.core.auth import CurrentUserDep
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.profile import service
from app.features.profile.schemas import (
    QuestionnaireIn,
    QuestionnaireResponse,
    SkillConfirmationIn,
    SkillConfirmationResponse,
)

router = APIRouter(prefix="/profile", tags=["profile"])

_CHUNK_BYTES = 64 * 1024


async def read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks and stop as soon as it exceeds `max_bytes`.

    Never allocates more than `max_bytes + one chunk`, so an oversized or endless upload
    cannot exhaust the worker's memory.
    """
    buf = bytearray()
    while chunk := await file.read(_CHUNK_BYTES):
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise AppError(
                f"File is larger than {max_bytes // (1024 * 1024)} MB",
                status_code=413,
                code="payload_too_large",
            )
    return bytes(buf)


# ---------------------------------------------------------------------------
# M2-02: Intake questionnaire
# ---------------------------------------------------------------------------


@router.post("/questionnaire", summary="Submit intake questionnaire (M2-02)")
def submit_questionnaire(data: QuestionnaireIn, user: CurrentUserDep) -> QuestionnaireResponse:
    """Save working segment, interests, learning preferences and HRD eligibility.

    Interests are sanitised against the fairness whitelist (M2-12) before
    being passed to the matching engine.
    """
    return service.upsert_questionnaire(user, data)


# ---------------------------------------------------------------------------
# Core profile CRUD (legacy / backward-compat)
# ---------------------------------------------------------------------------


@router.post("", summary="Upsert core profile fields")
def upsert_profile(data: ProfileIn, user: CurrentUserDep) -> Profile:
    return service.upsert_profile(user, data)


@router.get("/me", summary="Get current user profile")
def get_my_profile(user: CurrentUserDep) -> Profile:
    return service.get_my_profile(user)


# ---------------------------------------------------------------------------
# M2-01: CV upload and parsing
# ---------------------------------------------------------------------------


@router.post("/cv", summary="Upload CV for skill extraction (M2-01)")
async def upload_cv(file: UploadFile, user: CurrentUserDep) -> CvExtractionResult:
    """Accept a PDF or plain-text CV, extract skills against the taxonomy.

    The file is processed in memory and never stored (AGENTS.md §3 guardrails).
    Returns a list of ExtractedSkill objects ordered by confidence, each with
    a proficiency level on the 1-5 scale ready for the confirmation screen (M2-03).
    """
    content = await read_capped(file, get_settings().max_upload_bytes)
    return service.extract_cv(file.filename or "cv", content)


# ---------------------------------------------------------------------------
# M2-03: Skill confirmation screen
# ---------------------------------------------------------------------------


@router.put("/skills/confirm", summary="Confirm and persist final skill list (M2-03)")
def confirm_skills(data: SkillConfirmationIn, user: CurrentUserDep) -> SkillConfirmationResponse:
    """Persist the user-edited skill list after the confirmation screen.

    Validates that every skill_id exists in the taxonomy (no hallucinated skills).
    Normalises level 1-5 → 0.0-1.0 for the matching engine and returns both
    representations so the frontend can render the profile and the matching preview.
    """
    return service.confirm_skills(user, data)


@router.put("/skills", summary="Replace skill list (legacy)")
def replace_skills(data: SkillsUpdate, user: CurrentUserDep) -> Profile:
    """Legacy endpoint. Prefer PUT /profile/skills/confirm for new integrations."""
    return service.replace_skills(user, data.skills)
