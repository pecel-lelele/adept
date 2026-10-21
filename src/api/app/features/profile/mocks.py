"""Synthetic persona profiles (docs/PROJECT_CONTEXT.md §11.5). No real people."""

from app.contracts.profile import ExtractedSkill, Profile, UserSkill

PROFILES: dict[str, Profile] = {
    "aisyah": Profile(
        user_id="aisyah",
        display_name="Aisyah",
        segment="working",
        interests=["data", "finance", "process improvement"],
        hours_per_week=6,
        budget_myr=500,
        hrd_eligible=True,
        current_role_id="bank-operations-executive",
        skills=[
            UserSkill(skill_id="excel", level=4, source="confirmed"),
            UserSkill(skill_id="risk-compliance", level=3, source="confirmed"),
            UserSkill(skill_id="process-mapping", level=2, source="cv"),
            UserSkill(skill_id="customer-service", level=4, source="form"),
        ],
    ),
    "weijie": Profile(
        user_id="weijie",
        display_name="Wei Jie",
        segment="graduate",
        interests=["software", "AI"],
        hours_per_week=15,
        budget_myr=200,
        hrd_eligible=False,
        current_role_id=None,
        skills=[
            UserSkill(skill_id="python", level=2, source="cv"),
            UserSkill(skill_id="sql", level=2, source="cv"),
        ],
    ),
    "ravi": Profile(
        user_id="ravi",
        display_name="Ravi",
        segment="switcher",
        interests=["operations", "analytics"],
        hours_per_week=8,
        budget_myr=800,
        hrd_eligible=True,
        current_role_id="logistics-supervisor",
        skills=[
            UserSkill(skill_id="logistics-planning", level=4, source="confirmed"),
            UserSkill(skill_id="excel", level=3, source="form"),
        ],
    ),
    "demo-company": Profile(
        user_id="demo-company",
        display_name="Demo Bank HR",
        segment="working",
        interests=["finance", "operations", "data"],
        hours_per_week=10,
        budget_myr=1000,
        hrd_eligible=True,
        current_role_id="compliance-analytics-officer",
        skills=[
            UserSkill(skill_id="risk-compliance", level=3, source="confirmed"),
            UserSkill(skill_id="sql", level=2, source="confirmed"),
        ],
    ),
}

# Fixed mock result for POST /profile/cv; real extraction is an F1 open choice.
CV_EXTRACTION: list[ExtractedSkill] = [
    ExtractedSkill(skill_id="excel", label="Spreadsheet analysis", level=4, confidence=0.92),
    ExtractedSkill(skill_id="risk-compliance", label="Risk & compliance", level=3, confidence=0.81),
    ExtractedSkill(skill_id="process-mapping", label="Business process mapping", level=2,
                   confidence=0.64),
]  # fmt: skip
