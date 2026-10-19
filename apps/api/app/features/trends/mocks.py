"""Mock trend signals. Synthetic numbers; replace with snapshots from ingestion (F2)."""

from app.contracts.common import ScenarioId
from app.contracts.trends import TrendSignal

BASE_SIGNALS: list[TrendSignal] = [
    TrendSignal(entity_type="role", entity_id="data-analyst", label="Data Analyst",
                direction="rising", growth_rate=0.14, ai_exposure=0.55,
                automation_share=0.25, augmentation_share=0.75),
    TrendSignal(entity_type="role", entity_id="ai-operations-specialist",
                label="AI Operations Specialist", direction="rising", growth_rate=0.22,
                ai_exposure=0.70, automation_share=0.20, augmentation_share=0.80),
    TrendSignal(entity_type="role", entity_id="process-automation-analyst",
                label="Process Automation Analyst", direction="rising", growth_rate=0.18,
                ai_exposure=0.65, automation_share=0.30, augmentation_share=0.70),
    TrendSignal(entity_type="role", entity_id="compliance-analytics-officer",
                label="Compliance Analytics Officer", direction="stable", growth_rate=0.04,
                ai_exposure=0.45, automation_share=0.35, augmentation_share=0.65),
    TrendSignal(entity_type="role", entity_id="bank-operations-executive",
                label="Bank Operations Executive", direction="declining", growth_rate=-0.09,
                ai_exposure=0.80, automation_share=0.70, augmentation_share=0.30),
    TrendSignal(entity_type="role", entity_id="data-entry-clerk", label="Data Entry Clerk",
                direction="declining", growth_rate=-0.15, ai_exposure=0.90,
                automation_share=0.85, augmentation_share=0.15),
    TrendSignal(entity_type="skill", entity_id="prompt-engineering",
                label="Prompt engineering", direction="rising", growth_rate=0.30,
                ai_exposure=0.90, automation_share=0.10, augmentation_share=0.90),
    TrendSignal(entity_type="skill", entity_id="python", label="Python programming",
                direction="rising", growth_rate=0.12, ai_exposure=0.50,
                automation_share=0.20, augmentation_share=0.80),
    TrendSignal(entity_type="skill", entity_id="data-visualisation",
                label="Data visualisation", direction="rising", growth_rate=0.10,
                ai_exposure=0.40, automation_share=0.25, augmentation_share=0.75),
    TrendSignal(entity_type="skill", entity_id="excel", label="Spreadsheet analysis",
                direction="stable", growth_rate=0.01, ai_exposure=0.60,
                automation_share=0.50, augmentation_share=0.50),
    TrendSignal(entity_type="skill", entity_id="manual-data-entry", label="Manual data entry",
                direction="declining", growth_rate=-0.20, ai_exposure=0.95,
                automation_share=0.90, augmentation_share=0.10),
]  # fmt: skip

# Mock-only scenario effect so the UI visibly re-ranks; real values come from F3.
SCENARIO_GROWTH_FACTOR: dict[ScenarioId, float] = {"moderate": 1.0, "fast": 1.6}


def signals(scenario: ScenarioId) -> list[TrendSignal]:
    factor = SCENARIO_GROWTH_FACTOR[scenario]
    return [
        s.model_copy(update={"growth_rate": round(s.growth_rate * factor, 3)}) for s in BASE_SIGNALS
    ]
