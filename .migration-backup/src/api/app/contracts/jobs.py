"""Live job openings and certifications (owner M4): where a plan leads in today's market."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta

SkillStatus = Literal["have", "in_plan", "missing", "not_rated"]
WorkMode = Literal["onsite", "hybrid", "remote"]
Seniority = Literal["intern", "entry", "mid", "senior", "lead", "unknown"]
Payer = Literal["learner", "employer"]


class SkillAsk(BaseModel):
    skill_id: str
    label: str
    status: SkillStatus = Field(
        description=(
            "have: the learner already meets it; in_plan: their learning plan for this role "
            "reaches it; missing: neither; not_rated: no learner profile in this context "
            "(e.g. an HR manager viewing a team programme)."
        )
    )


class JobOpening(BaseModel):
    id: str
    title: str
    employer: str
    location: str
    work_mode: WorkMode
    remote_scope: str = Field(default="", description="Remote only: who may apply.")
    employment_type: str = ""
    seniority: Seniority = "unknown"
    url: str = Field(description="The employer's or job board's own ad; applications go there.")
    source_name: str = Field(description="Where the opening was read from (credited in the UI).")
    posted_at: date | None = None
    first_seen: date
    role_method: Literal["title", "skills"] = Field(
        description="How the opening was matched to the role: its job title, or its skills."
    )
    skills: list[SkillAsk] = Field(description="Catalogue skills the ad names.")
    cert_ids: list[str] = Field(default_factory=list, description="Certifications the ad names.")
    match_now: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Share of the ad's skills the learner has now; None if it names under two.",
    )
    match_after_plan: float | None = Field(
        default=None, ge=0, le=1, description="The same share once the plan is finished."
    )


class SkillDemand(BaseModel):
    skill_id: str
    label: str
    openings: int = Field(ge=0, description="Open roles of this kind whose ad names the skill.")
    share: float = Field(ge=0, le=1)
    status: SkillStatus


class RoleOpenings(BaseModel):
    role_id: str
    role_label: str
    open_count: int = Field(ge=0)
    employer_count: int = Field(ge=0)
    remote_count: int = Field(ge=0)
    employers: list[str] = Field(description="Employers with the most openings, most first.")
    openings: list[JobOpening]
    skill_demand: list[SkillDemand] = Field(description="Skills these ads ask for most.")
    ready_threshold: float = Field(
        description="An opening counts as within reach at this share of its skills or more."
    )
    ready_now: int = Field(ge=0, description="Openings within reach today.")
    ready_after_plan: int = Field(ge=0, description="Openings within reach after the plan.")
    rated: int = Field(ge=0, description="Openings that name enough skills to rate (>= 2).")
    has_plan: bool = Field(description="False when no plan could be built for this learner.")
    fetched_on: date | None = None
    meta: RecommendationMeta


class RoleOpeningCount(BaseModel):
    role_id: str
    role_label: str
    open_count: int = Field(ge=0)
    employer_count: int = Field(ge=0)
    remote_count: int = Field(ge=0)


class OpeningsSummary(BaseModel):
    roles: list[RoleOpeningCount]
    total_open: int = Field(ge=0)
    employer_count: int = Field(ge=0)
    fetched_on: date | None = None
    meta: RecommendationMeta


class JobBoardPage(BaseModel):
    """Every live opening matched to an Adept role, filtered and paged."""

    openings: list[JobOpening]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    roles: list[RoleOpeningCount]
    fetched_on: date | None = None
    meta: RecommendationMeta


class Certification(BaseModel):
    id: str
    name: str
    issuer: str
    exam_code: str
    url: str
    level: Literal["foundational", "associate", "professional"]
    fee_amount: float = Field(ge=0)
    fee_currency: str
    fee_myr: float = Field(ge=0)
    fee_note: str
    fee_source_url: str
    verified_at: date
    validity_note: str = ""
    skills: list[SkillAsk] = Field(description="Skills the exam covers, with the learner's status.")
    role_skills: int = Field(ge=0, description="How many of the role's required skills it covers.")
    prep_course_ids: list[str] = Field(
        default_factory=list, description="Courses in the learner's plan that teach its skills."
    )
    openings_naming: int = Field(
        ge=0, description="Current openings for this role whose ad names this certification."
    )


class CertificationList(BaseModel):
    role_id: str
    role_label: str
    payer: Payer = Field(
        description=(
            "Who normally pays the exam fee in this context: the learner on a personal plan, "
            "the employer on a team programme. Adept never takes payment."
        )
    )
    certifications: list[Certification]
    meta: RecommendationMeta
