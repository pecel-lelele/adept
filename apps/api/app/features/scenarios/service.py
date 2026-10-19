"""Scenario logic (F3). Outlook formula and range method are open choices for M1."""

from app.contracts.common import mock_meta
from app.contracts.scenarios import OutlookResponse, ScenarioListResponse
from app.core.errors import NotFoundError
from app.features.scenarios import repository


def list_scenarios() -> ScenarioListResponse:
    return ScenarioListResponse(scenarios=repository.list_scenarios(), meta=mock_meta())


def get_outlook(role_id: str | None) -> OutlookResponse:
    outlooks = repository.list_outlooks(role_id)
    if role_id is not None and not outlooks:
        raise NotFoundError(f"No outlook for role {role_id}")
    return OutlookResponse(outlooks=outlooks, meta=mock_meta())
