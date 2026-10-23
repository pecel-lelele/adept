"""Synthetic test fixtures (docs/PROJECT_CONTEXT.md §11.5). No real people.

The running app has no built-in personas: every account, profile and organisation is
created through sign-up. The automated tests run on the in-memory stores
(M3_BACKEND=csv) and install these fixtures there.
"""

from app.contracts.org import Member, Organization
from app.contracts.profile import Profile, UserSkill
from app.core import accounts
from app.features.org import repository as org_repository
from app.features.profile import repository as profile_repository

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

ORGS: dict[str, Organization] = {
    "org-demo-bank": Organization(id="org-demo-bank", type="company", name="Demo Bank Berhad",
                                  industry="Banking & financial services", size=25),
    "org-demo-poly": Organization(id="org-demo-poly", type="institution",
                                  name="Demo Polytechnic Career Centre", industry="TVET",
                                  size=40),
}  # fmt: skip

MEMBERS: dict[str, list[Member]] = {
    "org-demo-bank": [
        Member(id="aisyah", display_name="Aisyah", current_role_id="bank-operations-executive",
               intake_status="complete"),
        Member(id="emp-002", display_name="Employee 002", current_role_id="data-entry-clerk",
               intake_status="complete"),
        Member(id="emp-003", display_name="Employee 003",
               current_role_id="bank-operations-executive", intake_status="in_progress"),
        Member(id="emp-004", display_name="Employee 004", current_role_id=None,
               intake_status="invited"),
    ],
    "org-demo-poly": [
        Member(id="weijie", display_name="Wei Jie", current_role_id=None,
               intake_status="complete"),
        Member(id="stu-002", display_name="Student 002", current_role_id=None,
               intake_status="invited"),
    ],
}  # fmt: skip

# Synthetic confirmed skills for team members who have no persona profile (F1). Members with
# a profile (e.g. Aisyah, Wei Jie) use their profile instead. Levels 1-5. No real people.
TEAM_SKILLS: dict[str, dict[str, int]] = {
    "emp-002": {"excel": 3, "manual-data-entry": 4, "customer-service": 2},
    "emp-003": {"excel": 4, "risk-compliance": 2, "process-mapping": 1},
}


ACCOUNTS: list[accounts.Account] = [
    accounts.Account("aisyah", "Aisyah", None, "learner", "org-demo-bank"),
    accounts.Account("weijie", "Wei Jie", None, "learner"),
    accounts.Account("ravi", "Ravi", None, "learner"),
    accounts.Account("demo-company", "Demo Bank HR", None, "org_admin", "org-demo-bank"),
    accounts.Account(
        "demo-institution", "Demo Polytechnic Career Centre", None, "org_admin", "org-demo-poly"
    ),
]
JOIN_CODES = {"org-demo-bank": "BANKDEMO", "org-demo-poly": "POLYDEMO"}


def install() -> None:
    """(Re)install every fixture into the in-memory stores."""
    accounts.reset()
    for account in ACCOUNTS:
        accounts.create(account, "")
    profile_repository._store.clear()
    profile_repository._store.update({k: v.model_copy(deep=True) for k, v in PROFILES.items()})
    for member_id, levels in TEAM_SKILLS.items():
        member = next(m for ms in MEMBERS.values() for m in ms if m.id == member_id)
        profile_repository._store[member_id] = Profile(
            user_id=member_id,
            display_name=member.display_name,
            segment="working",
            interests=[],
            hours_per_week=0,
            budget_myr=0,
            hrd_eligible=False,
            current_role_id=member.current_role_id,
            skills=[UserSkill(skill_id=s, level=v, source="confirmed") for s, v in levels.items()],
        )
    org_repository.reset()
    for org_id, org in ORGS.items():
        org_repository._orgs[org_id] = org.model_copy(update={"join_code": JOIN_CODES[org_id]})
        # The synthetic teams chose to share their skill levels with their organisation.
        org_repository._members[org_id] = [
            m.model_copy(update={"skills_shared": True}) for m in MEMBERS[org_id]
        ]
