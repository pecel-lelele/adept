"""Profile intake logic (F1). CV parsing and extraction are open choices for M2."""

from app.contracts.common import mock_meta
from app.contracts.profile import CvExtractionResult, Profile, ProfileIn, UserSkill
from app.core.auth import CurrentUser
from app.features.profile import mocks, repository


def get_my_profile(user: CurrentUser) -> Profile:
    existing = repository.get_profile(user.id)
    if existing is not None:
        return existing
    return Profile(
        user_id=user.id,
        display_name=user.display_name,
        segment="working",
        hours_per_week=0,
        budget_myr=0,
        hrd_eligible=False,
        skills=[],
    )


def upsert_profile(user: CurrentUser, data: ProfileIn) -> Profile:
    current = get_my_profile(user)
    return repository.save_profile(current.model_copy(update=data.model_dump()))


def replace_skills(user: CurrentUser, skills: list[UserSkill]) -> Profile:
    current = get_my_profile(user)
    return repository.save_profile(current.model_copy(update={"skills": skills}))


def extract_cv(filename: str, content: bytes) -> CvExtractionResult:
    # Mock: ignores the file. Never store uploaded CVs; demo uses synthetic CVs only.
    return CvExtractionResult(skills=mocks.CV_EXTRACTION, meta=mock_meta())
