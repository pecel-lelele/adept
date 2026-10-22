"""Profile service layer (F1).

Business logic for M2-01, M2-02, and M2-03:
  - M2-01 extract_cv_real(): CV parsing pipeline via cv_parser.py
  - M2-02 upsert_questionnaire(): intake questionnaire → profile persistence
  - M2-03 confirm_skills(): user confirmation + normalisation + persistence

The matching engine (scoring.py) expects skill levels as floats in [0, 1].
Normalisation formula: (level - 1) / 4.0   (level 1 → 0.0, level 5 → 1.0)
"""

from __future__ import annotations

import csv
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.contracts.common import RecommendationMeta, Source
from app.contracts.profile import (
    CvExtractionResult,
    ExtractedSkill,
    Profile,
    ProfileIn,
    SkillCatalogueResponse,
    SkillOption,
    UserSkill,
)
from app.core.auth import CurrentUser
from app.core.errors import AppError
from app.features.org import repository as org_repository
from app.features.profile import repository
from app.features.profile.cv_parser import parse_cv
from app.features.profile.schemas import (
    NormalisedSkill,
    QuestionnaireIn,
    QuestionnaireResponse,
    SkillConfirmationIn,
    SkillConfirmationResponse,
)

# Extracted skills are matched against the Adept taxonomy; levels and confidence are estimates.
TAXONOMY_META = RecommendationMeta(
    sources=[
        Source(
            name="Adept skill taxonomy (skills.csv)",
            url="https://github.com/pecel-lelele/adept/blob/main/src/data/seed/taxonomy/skills.csv",
            retrieved_at=date(2026, 10, 22),
        )
    ],
    snapshot_date=date(2026, 10, 22),
    scenario="moderate",
    is_estimate=True,
)

_SEED = Path(__file__).resolve().parents[5] / "src" / "data" / "seed"

# ---------------------------------------------------------------------------
# Taxonomy helpers (shared across the service)
# ---------------------------------------------------------------------------

# M2-12 fairness whitelist: only non-demographic interest tags are permitted.
# Demographic signals (age, gender, race, religion, disability) must never
# reach the matching engine's MatchProfile.
BLOCKED_DEMOGRAPHIC_INTERESTS: frozenset[str] = frozenset(
    {"age", "gender", "race", "ethnicity", "religion", "nationality", "disability"}
)


def _normalise_interest_text(text: str) -> str:
    """Normalise interest: lowercase, strip punctuation, collapse whitespace."""
    no_punct = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", no_punct).strip().lower()


def _sanitise_interests(raw: list[str]) -> list[str]:
    """Strip any interest tags that match blocked demographic attributes (M2-12).

    Normalises each tag (lowercase, strip punctuation, collapse spaces) and drops
    an interest only when the whole normalised text equals one of the blocked
    demographic tokens. Substring and prefix matches (e.g. 'agentic AI',
    'management', 'age-friendly design') are preserved.
    """
    cleaned: list[str] = []
    for tag in raw:
        norm = _normalise_interest_text(tag)
        if norm and norm in BLOCKED_DEMOGRAPHIC_INTERESTS:
            continue
        cleaned.append(tag.strip())
    return cleaned


@lru_cache(maxsize=1)
def _skill_labels() -> dict[str, str]:
    """Map skill_id → human-readable label from taxonomy/skills.csv."""
    path = _SEED / "taxonomy" / "skills.csv"
    labels: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            labels[row["id"]] = row["label"]
    return labels


def skill_catalogue() -> SkillCatalogueResponse:
    """Every taxonomy skill, sorted by label, for the skill picker."""
    path = _SEED / "taxonomy" / "skills.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    options = [
        SkillOption(id=r["id"], label=r["label"], group=r.get("description") or "") for r in rows
    ]
    with open(_SEED / "taxonomy" / "roles.csv", encoding="utf-8") as f:
        tags = {
            tag.strip()
            for row in csv.DictReader(f)
            for tag in (row.get("interest_tags") or "").split("|")
            if tag.strip()
        }
    return SkillCatalogueResponse(
        skills=sorted(options, key=lambda o: o.label.lower()),
        interests=sorted(tags, key=str.lower),
    )


@lru_cache(maxsize=1)
def _valid_skill_ids() -> frozenset[str]:
    """Return the set of valid taxonomy skill IDs."""
    return frozenset(_skill_labels().keys())


def normalise_level(level: int) -> float:
    """Map integer level 1-5 → float 0.0-1.0 for the scoring engine."""
    return (level - 1) / 4.0


# ---------------------------------------------------------------------------
# M2-01: CV parsing + extraction
# ---------------------------------------------------------------------------


def extract_cv(
    filename: str,
    content: bytes,
    content_type: str = "text/plain",
) -> CvExtractionResult:
    """Run the real CV parsing pipeline and return structured results.

    Raises:
        PdfSupportUnavailable: fitz absent and a PDF was uploaded.
        PdfNoText:             PDF has no extractable text.
    """
    parsed, truncated = parse_cv(content, content_type)
    labels = _skill_labels()

    skills = [
        ExtractedSkill(
            skill_id=ps.skill_id,
            label=labels.get(ps.skill_id, ps.skill_id),
            level=ps.level,
            confidence=ps.confidence,
        )
        for ps in parsed
    ]

    return CvExtractionResult(skills=skills, truncated=truncated, meta=TAXONOMY_META)


# ---------------------------------------------------------------------------
# M2-02: Profile intake questionnaire
# ---------------------------------------------------------------------------


def get_my_profile(user: CurrentUser | str) -> Profile:
    """Load profile from in-memory store; return a default for unknown users."""
    user_id = user if isinstance(user, str) else user.id
    display_name = user_id if isinstance(user, str) else user.display_name
    existing = repository.get_profile(user_id)
    if existing is not None:
        return existing
    return Profile(
        user_id=user_id,
        display_name=display_name,
        segment="working",
        interests=[],
        hours_per_week=0,
        budget_myr=0,
        hrd_eligible=False,
        skills=[],
    )


def has_profile(user_id: str) -> bool:
    """Return True if the user has an existing saved profile."""
    return repository.get_profile(user_id) is not None


def upsert_profile(user: CurrentUser, data: ProfileIn) -> Profile:
    """Update core profile fields (segment, interests, hours, budget, HRD)."""
    current = get_my_profile(user)
    # Sanitise interests for the fairness whitelist
    clean_data = data.model_dump()
    clean_data["interests"] = _sanitise_interests(clean_data.get("interests", []))
    if "learning_style" not in data.model_fields_set:
        clean_data.pop("learning_style")  # keep the saved choice when a form omits it
    return repository.save_profile(current.model_copy(update=clean_data))


def upsert_questionnaire(user: CurrentUser, data: QuestionnaireIn) -> QuestionnaireResponse:
    """Persist full questionnaire intake (M2-02).

    Stores the ProfileIn-compatible fields and returns a confirmation with
    the learning_style field (which lives only in the feature schema).
    """
    # Build the ProfileIn-compatible subset for storage
    profile_data = ProfileIn(
        segment=data.segment,
        interests=_sanitise_interests(data.interests),
        hours_per_week=data.hours_per_week,
        budget_myr=data.budget_myr,
        hrd_eligible=data.hrd_eligible,
        learning_style=data.learning_style,
    )
    saved = upsert_profile(user, profile_data)
    org_repository.set_intake_status(user.id, "complete" if saved.skills else "in_progress")

    return QuestionnaireResponse(
        user_id=saved.user_id,
        display_name=saved.display_name,
        segment=saved.segment,
        interests=saved.interests,
        hours_per_week=saved.hours_per_week,
        learning_style=saved.learning_style,
        budget_myr=saved.budget_myr,
        hrd_eligible=saved.hrd_eligible,
    )


# ---------------------------------------------------------------------------
# M2-03: Skill confirmation and persistence
# ---------------------------------------------------------------------------


def replace_skills(user: CurrentUser, skills: list[UserSkill]) -> Profile:
    """Replace the user's skill list (used by the legacy PUT /profile/skills)."""
    current = get_my_profile(user)
    saved = repository.save_profile(current.model_copy(update={"skills": skills}))
    org_repository.set_intake_status(user.id, "complete" if skills else "in_progress")
    return saved


def confirm_skills(user: CurrentUser, data: SkillConfirmationIn) -> SkillConfirmationResponse:
    """Validate, normalise, and persist confirmed skills (M2-03).

    Validation rules:
      - Every skill_id must exist in the taxonomy (no hallucinated skills).
      - Duplicate skill_ids are rejected (last-write would be silent and confusing).

    Normalisation:
      - Converts level 1-5 → 0.0-1.0 using (level - 1) / 4.0
      - This matches exactly what scoring.py expects from user_skills.csv.
    """
    labels = _skill_labels()
    valid_ids = _valid_skill_ids()

    # Validate all submitted skill IDs
    unknown = [s.skill_id for s in data.skills if s.skill_id not in valid_ids]
    if unknown:
        raise AppError(
            f"Unknown skill IDs: {', '.join(unknown)}. "
            "Only taxonomy-registered skills are accepted.",
            status_code=422,
            code="unknown_skill_ids",
        )

    # Reject duplicates
    seen: set[str] = set()
    duplicates: list[str] = []
    for s in data.skills:
        if s.skill_id in seen:
            duplicates.append(s.skill_id)
        else:
            seen.add(s.skill_id)
    if duplicates:
        raise AppError(
            f"Duplicate skill IDs: {', '.join(duplicates)}. Submit each skill once.",
            status_code=422,
            code="duplicate_skill_ids",
        )

    # Build UserSkill list (contracts form, level 1-5 preserved for the profile)
    confirmed: list[UserSkill] = [
        UserSkill(skill_id=s.skill_id, level=s.level, source="confirmed") for s in data.skills
    ]

    # Persist
    current = get_my_profile(user)
    repository.save_profile(current.model_copy(update={"skills": confirmed}))
    org_repository.set_intake_status(user.id, "complete" if confirmed else "in_progress")

    # Build normalised view for the API response
    normalised: list[NormalisedSkill] = [
        NormalisedSkill(
            skill_id=s.skill_id,
            label=labels.get(s.skill_id, s.skill_id),
            level=s.level,
            normalised_level=round(normalise_level(s.level), 4),
        )
        for s in data.skills
    ]

    return SkillConfirmationResponse(
        user_id=user.id,
        confirmed_skills=confirmed,
        normalised_skills=normalised,
    )
