"""Mock role matches for the demo persona. Synthetic values; real scoring is F4 (M2)."""

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.matching import RoleMatch, ScoreComponent
from app.contracts.profile import Skill
from app.contracts.sdg import SdgTarget

SKILLS = {
    "python": Skill(id="python", label="Python programming"),
    "sql": Skill(id="sql", label="SQL"),
    "data-visualisation": Skill(id="data-visualisation", label="Data visualisation"),
    "rpa": Skill(id="rpa", label="Robotic process automation"),
    "prompt-engineering": Skill(id="prompt-engineering", label="Prompt engineering"),
    "process-mapping": Skill(id="process-mapping", label="Business process mapping"),
    "ai-literacy": Skill(id="ai-literacy", label="AI literacy & responsible AI"),
}
SDG_4_4 = SdgTarget(goal=4, target="4.4", label="Relevant skills for employment and decent jobs")
SDG_8_2 = SdgTarget(goal=8, target="8.2", label="Productivity through technology and innovation")
SDG_8_5 = SdgTarget(goal=8, target="8.5", label="Full and productive employment for all")

# role_id: (label, skill_overlap, trend by scenario, interest_fit, missing, partial, sdg)
_ROLES: dict[str, tuple[str, float, dict[ScenarioId, float], float, list[str], list[str],
                        list[SdgTarget]]] = {
    "process-automation-analyst": ("Process Automation Analyst", 0.60,
        {"moderate": 0.75, "fast": 0.90}, 0.80, ["rpa"], ["process-mapping"], [SDG_8_2, SDG_4_4]),
    "data-analyst": ("Data Analyst", 0.50, {"moderate": 0.80, "fast": 0.85}, 0.90,
        ["python", "sql"], ["data-visualisation"], [SDG_4_4, SDG_8_5]),
    "compliance-analytics-officer": ("Compliance Analytics Officer", 0.70,
        {"moderate": 0.70, "fast": 0.50}, 0.60, ["sql"], ["data-visualisation"], [SDG_8_5]),
    "ai-operations-specialist": ("AI Operations Specialist", 0.30,
        {"moderate": 0.85, "fast": 0.95}, 0.70, ["prompt-engineering", "python"], ["ai-literacy"],
        [SDG_8_2, SDG_4_4]),
}  # fmt: skip

WEIGHTS = {"skill_overlap": 0.5, "trend_outlook": 0.3, "interest_fit": 0.2}


def _match(role_id: str, scenario: ScenarioId) -> RoleMatch:
    label, overlap, trend, interest, missing, partial, sdg = _ROLES[role_id]
    components = [
        ScoreComponent(name="skill_overlap", weight=WEIGHTS["skill_overlap"], value=overlap,
                       explanation="Share of required skills you already have (mock)."),
        ScoreComponent(name="trend_outlook", weight=WEIGHTS["trend_outlook"],
                       value=trend[scenario],
                       explanation=f"Projected demand under the {scenario} scenario (mock)."),
        ScoreComponent(name="interest_fit", weight=WEIGHTS["interest_fit"], value=interest,
                       explanation="Fit with the interests in your profile (mock)."),
    ]  # fmt: skip
    return RoleMatch(
        role_id=role_id,
        label=label,
        score=round(sum(c.weight * c.value for c in components), 3),
        components=components,
        missing_skills=[SKILLS[s] for s in missing],
        partial_skills=[SKILLS[s] for s in partial],
        sdg_targets=sdg,
        meta=mock_meta(scenario),
    )


def matches(scenario: ScenarioId) -> list[RoleMatch]:
    return sorted((_match(r, scenario) for r in _ROLES), key=lambda m: m.score, reverse=True)


def match(role_id: str, scenario: ScenarioId) -> RoleMatch | None:
    return _match(role_id, scenario) if role_id in _ROLES else None
