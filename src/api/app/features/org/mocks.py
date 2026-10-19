"""Mock organisations (synthetic). The full demo company has 25 synthetic employees; a few
are listed here. F7 (M4) moves this to `organizations` and `memberships`."""

from app.contracts.org import Member, Organization

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

# Roles shown as heatmap rows. Cells are computed from members' skills (F5 `team_gaps`).
GAP_ROLES = ["data-analyst", "process-automation-analyst"]

# Synthetic confirmed skills for team members who have no persona profile (F1). Members with
# a profile (e.g. Aisyah, Wei Jie) use their profile instead. Levels 1-5. No real people.
TEAM_SKILLS: dict[str, dict[str, int]] = {
    "emp-002": {"excel": 3, "manual-data-entry": 4, "customer-service": 2},
    "emp-003": {"excel": 4, "risk-compliance": 2, "process-mapping": 1},
}

# Target role a manager plans for when none is chosen yet (per organisation).
DEFAULT_TARGET_ROLE: dict[str, str] = {
    "org-demo-bank": "process-automation-analyst",
    "org-demo-poly": "data-analyst",
}
