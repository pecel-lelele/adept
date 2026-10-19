"""Data access for trends. Reads mocks for now; later `snapshots` + `trend_signals`."""

from app.contracts.common import ScenarioId
from app.contracts.trends import EntityType, TrendSignal
from app.features.trends import mocks


def list_signals(scenario: ScenarioId) -> list[TrendSignal]:
    return mocks.signals(scenario)


def get_signal(entity_type: EntityType, entity_id: str, scenario: ScenarioId) -> TrendSignal | None:
    return next(
        (
            s
            for s in mocks.signals(scenario)
            if s.entity_type == entity_type and s.entity_id == entity_id
        ),
        None,
    )
