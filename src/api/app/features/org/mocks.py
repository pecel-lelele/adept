"""Mock organisations (synthetic). The full demo company has 25 synthetic employees; a few
are listed here. F7 (M4) moves this to `organizations` and `memberships`."""

from app.contracts.org import GapHeatmapCell, Member, Organization
from app.contracts.profile import Skill

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

GAP_SKILLS = [
    Skill(id="sql", label="SQL"),
    Skill(id="python", label="Python programming"),
    Skill(id="rpa", label="Robotic process automation"),
    Skill(id="ai-literacy", label="AI literacy & responsible AI"),
]
GAP_ROLES = ["data-analyst", "process-automation-analyst"]
# (role_id, skill_id) -> base gap; the fast scenario widens gaps in this mock.
GAPS: dict[tuple[str, str], float] = {
    ("data-analyst", "sql"): 0.72,
    ("data-analyst", "python"): 0.84,
    ("data-analyst", "rpa"): 0.20,
    ("data-analyst", "ai-literacy"): 0.55,
    ("process-automation-analyst", "sql"): 0.40,
    ("process-automation-analyst", "python"): 0.60,
    ("process-automation-analyst", "rpa"): 0.90,
    ("process-automation-analyst", "ai-literacy"): 0.50,
}


def heatmap(widen: float) -> list[GapHeatmapCell]:
    return [
        GapHeatmapCell(role_id=r, skill_id=s, gap=min(1.0, round(g * widen, 2)))
        for (r, s), g in GAPS.items()
    ]
