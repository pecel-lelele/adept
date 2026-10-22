"""Data access for scenarios (F3): trend snapshots (F2) and role requirements (taxonomy)."""

from __future__ import annotations

from datetime import date

from app.contracts.common import ScenarioId
from app.contracts.trends import TrendSnapshotResponse
from app.features.pathway import data as pathway_data
from app.features.trends import service as trends_service


def snapshot(scenario: ScenarioId, snapshot_date: date | None = None) -> TrendSnapshotResponse:
    return trends_service.get_snapshot(snapshot_date, scenario)


def role_requirements(role_id: str) -> list[pathway_data.Requirement]:
    return pathway_data.requirements(role_id)


def target_role_ids() -> list[str]:
    return pathway_data.target_role_ids()
