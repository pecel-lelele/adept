"""Trend logic (F2). Scoring formula and ingestion are open choices for M1."""

from app.contracts.common import ScenarioId, mock_meta
from app.contracts.trends import RadarResponse, RoleTrendResponse
from app.core.errors import NotFoundError
from app.features.trends import repository


def get_radar(scenario: ScenarioId) -> RadarResponse:
    return RadarResponse(items=repository.list_signals(scenario), meta=mock_meta(scenario))


def get_role_trend(role_id: str, scenario: ScenarioId) -> RoleTrendResponse:
    signal = repository.get_signal("role", role_id, scenario)
    if signal is None:
        raise NotFoundError(f"No trend signal for role {role_id}")
    return RoleTrendResponse(signal=signal, meta=mock_meta(scenario))
