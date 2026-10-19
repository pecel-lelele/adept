"""Mock SDG links. Target labels are short forms of the official UN targets; the reasons
are MOCK text pending F6 (M3) mapping and human review."""

from app.contracts.sdg import GoalSummary, SdgLink, SdgTarget

TARGETS: dict[str, SdgTarget] = {
    "4.3": SdgTarget(goal=4, target="4.3",
                     label="Equal access to technical, vocational and tertiary education"),
    "4.4": SdgTarget(goal=4, target="4.4",
                     label="Relevant skills for employment, decent jobs and entrepreneurship"),
    "8.2": SdgTarget(goal=8, target="8.2",
                     label="Higher productivity through technological upgrading and innovation"),
    "8.5": SdgTarget(goal=8, target="8.5",
                     label="Full and productive employment and decent work for all"),
    "9.5": SdgTarget(goal=9, target="9.5",
                     label="Enhance research and upgrade technological capabilities"),
}  # fmt: skip

GOAL_LABELS = {
    4: "Quality Education",
    8: "Decent Work and Economic Growth",
    9: "Industry, Innovation and Infrastructure",
}

ROLE_LINKS: dict[str, list[tuple[str, str]]] = {
    "data-analyst": [("8.2", "Data-driven decisions raise productivity (mock reason)."),
                     ("4.4", "In-demand digital skill for decent work (mock reason).")],
    "process-automation-analyst": [("8.2", "Automates routine work (mock reason)."),
                                   ("9.5", "Upgrades technological capability (mock reason).")],
    "ai-operations-specialist": [("9.5", "Operates AI systems responsibly (mock reason).")],
    "compliance-analytics-officer": [("8.5", "Keeps workers employed as roles shift (mock).")],
}  # fmt: skip

SKILL_LINKS: dict[str, list[tuple[str, str]]] = {
    "python": [("4.4", "Programming is a relevant skill for employment (mock reason).")],
    "sql": [("4.4", "Data skills are relevant for decent jobs (mock reason).")],
    "rpa": [("8.2", "Automation skills raise productivity (mock reason).")],
}


def links(table: dict[str, list[tuple[str, str]]], entity_id: str) -> list[SdgLink]:
    return [SdgLink(target=TARGETS[t], reason=r) for t, r in table.get(entity_id, [])]


def summarise(items: list[SdgLink]) -> list[GoalSummary]:
    counts: dict[int, int] = {}
    for link in items:
        counts[link.target.goal] = counts.get(link.target.goal, 0) + 1
    return [
        GoalSummary(goal=g, label=GOAL_LABELS.get(g, f"SDG {g}"), link_count=n)
        for g, n in sorted(counts.items())
    ]
