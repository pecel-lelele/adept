from fastapi import APIRouter, UploadFile

from app.contracts.profile import CvExtractionResult, Profile, ProfileIn, SkillsUpdate
from app.core.auth import CurrentUserDep
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.profile import service

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


@router.post("")
def upsert_profile(data: ProfileIn, user: CurrentUserDep) -> Profile:
    return service.upsert_profile(user, data)


@router.get("/me")
def get_my_profile(user: CurrentUserDep) -> Profile:
    return service.get_my_profile(user)


@router.post("/cv")
async def upload_cv(file: UploadFile, user: CurrentUserDep) -> CvExtractionResult:
    content = await read_capped(file, get_settings().max_upload_bytes)
    return service.extract_cv(file.filename or "cv", content)


@router.put("/skills")
def replace_skills(data: SkillsUpdate, user: CurrentUserDep) -> Profile:
    return service.replace_skills(user, data.skills)
