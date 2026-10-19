from fastapi import APIRouter, UploadFile

from app.contracts.profile import CvExtractionResult, Profile, ProfileIn, SkillsUpdate
from app.core.auth import CurrentUserDep
from app.features.profile import service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("")
def upsert_profile(data: ProfileIn, user: CurrentUserDep) -> Profile:
    return service.upsert_profile(user, data)


@router.get("/me")
def get_my_profile(user: CurrentUserDep) -> Profile:
    return service.get_my_profile(user)


@router.post("/cv")
async def upload_cv(file: UploadFile, user: CurrentUserDep) -> CvExtractionResult:
    content = await file.read()
    return service.extract_cv(file.filename or "cv", content)


@router.put("/skills")
def replace_skills(data: SkillsUpdate, user: CurrentUserDep) -> Profile:
    return service.replace_skills(user, data.skills)
