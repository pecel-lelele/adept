"""Mock scenarios and outlooks. Parameters are placeholders until M1 sources them (F3)."""

from app.contracts.common import ScenarioId
from app.contracts.scenarios import RoleOutlook, Scenario

SCENARIOS: list[Scenario] = [
    Scenario(
        id="moderate",
        label="Moderate AI disruption",
        adoption_rate=0.35,
        description="AI tools spread gradually; most roles change rather than disappear.",
    ),
    Scenario(
        id="fast",
        label="Fast AI disruption",
        adoption_rate=0.65,
        description="Rapid adoption; routine back-office tasks are automated within 3-5 years.",
    ),
]

# role_id -> {scenario: (outlook, low, high)}
OUTLOOKS: dict[str, dict[ScenarioId, tuple[float, float, float]]] = {
    "data-analyst": {"moderate": (1.15, 1.05, 1.25), "fast": (1.30, 1.10, 1.50)},
    "ai-operations-specialist": {"moderate": (1.25, 1.10, 1.40), "fast": (1.50, 1.20, 1.80)},
    "process-automation-analyst": {"moderate": (1.20, 1.05, 1.35), "fast": (1.40, 1.15, 1.65)},
    "compliance-analytics-officer": {"moderate": (1.05, 0.95, 1.15), "fast": (1.10, 0.95, 1.25)},
    "bank-operations-executive": {"moderate": (0.90, 0.80, 0.97), "fast": (0.70, 0.55, 0.85)},
    "data-entry-clerk": {"moderate": (0.80, 0.70, 0.90), "fast": (0.55, 0.40, 0.70)},
}


def outlooks(role_id: str | None) -> list[RoleOutlook]:
    items = OUTLOOKS.items() if role_id is None else [(role_id, OUTLOOKS.get(role_id, {}))]
    return [
        RoleOutlook(role_id=rid, scenario=scenario, outlook=o, low=lo, high=hi)
        for rid, by_scenario in items
        for scenario, (o, lo, hi) in by_scenario.items()
    ]
