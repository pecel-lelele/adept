"""Mock snapshot fixture for the TrendSnapshotResponse contract.

Loaded from src/data/seed/mock_trends.json at import time (no network call,
no DB dependency). Wire this into repository.py so the endpoint is callable
before live pipeline data is available.

Both scenario variants are generated here:
  - moderate: loaded verbatim from the JSON (meta.scenario already = "moderate")
  - fast:     meta.scenario replaced, each item's velocity_fast and
              direction_fast promoted to the moderate fields so the frontend
              ScenarioToggle sees visibly different results.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.contracts.common import ScenarioId
from app.contracts.trends import (
    SkillVelocity,
    TrendSignal,
    TrendSnapshotMeta,
    TrendSnapshotResponse,
)

BASE_SIGNALS: list[TrendSignal] = [
    TrendSignal(
        entity_type="role",
        entity_id="data-analyst",
        label="Data Analyst",
        direction="rising",
        growth_rate=0.14,
        ai_exposure=0.55,
        automation_share=0.25,
        augmentation_share=0.75,
    ),
    TrendSignal(
        entity_type="role",
        entity_id="ai-operations-specialist",
        label="AI Operations Specialist",
        direction="rising",
        growth_rate=0.22,
        ai_exposure=0.70,
        automation_share=0.20,
        augmentation_share=0.80,
    ),
    TrendSignal(
        entity_type="role",
        entity_id="process-automation-analyst",
        label="Process Automation Analyst",
        direction="rising",
        growth_rate=0.18,
        ai_exposure=0.65,
        automation_share=0.30,
        augmentation_share=0.70,
    ),
    TrendSignal(
        entity_type="role",
        entity_id="compliance-analytics-officer",
        label="Compliance Analytics Officer",
        direction="stable",
        growth_rate=0.04,
        ai_exposure=0.45,
        automation_share=0.35,
        augmentation_share=0.65,
    ),
    TrendSignal(
        entity_type="role",
        entity_id="bank-operations-executive",
        label="Bank Operations Executive",
        direction="declining",
        growth_rate=-0.09,
        ai_exposure=0.80,
        automation_share=0.70,
        augmentation_share=0.30,
    ),
    TrendSignal(
        entity_type="role",
        entity_id="data-entry-clerk",
        label="Data Entry Clerk",
        direction="declining",
        growth_rate=-0.15,
        ai_exposure=0.90,
        automation_share=0.85,
        augmentation_share=0.15,
    ),
    TrendSignal(
        entity_type="skill",
        entity_id="prompt-engineering",
        label="Prompt engineering",
        direction="rising",
        growth_rate=0.30,
        ai_exposure=0.90,
        automation_share=0.10,
        augmentation_share=0.90,
    ),
    TrendSignal(
        entity_type="skill",
        entity_id="python",
        label="Python programming",
        direction="rising",
        growth_rate=0.12,
        ai_exposure=0.50,
        automation_share=0.20,
        augmentation_share=0.80,
    ),
    TrendSignal(
        entity_type="skill",
        entity_id="data-visualisation",
        label="Data visualisation",
        direction="rising",
        growth_rate=0.10,
        ai_exposure=0.40,
        automation_share=0.25,
        augmentation_share=0.75,
    ),
    TrendSignal(
        entity_type="skill",
        entity_id="excel",
        label="Spreadsheet analysis",
        direction="stable",
        growth_rate=0.01,
        ai_exposure=0.60,
        automation_share=0.50,
        augmentation_share=0.50,
    ),
    TrendSignal(
        entity_type="skill",
        entity_id="manual-data-entry",
        label="Manual data entry",
        direction="declining",
        growth_rate=-0.20,
        ai_exposure=0.95,
        automation_share=0.90,
        augmentation_share=0.10,
    ),
]

SCENARIO_GROWTH_FACTOR: dict[ScenarioId, float] = {"moderate": 1.0, "fast": 1.6}


def signals(scenario: ScenarioId) -> list[TrendSignal]:
    factor = SCENARIO_GROWTH_FACTOR[scenario]
    return [
        s.model_copy(update={"growth_rate": round(s.growth_rate * factor, 3)}) for s in BASE_SIGNALS
    ]


AVAILABLE_MOCK_DATES: list[date] = [date(2026, 10, 13), date(2026, 10, 20)]

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SEED_DIR = _REPO_ROOT / "src" / "data" / "seed"
_MOCK_FILE = _SEED_DIR / "mock_trends.json"


def _load_raw(snapshot_date: date | None = None) -> dict:
    if snapshot_date is not None:
        dated_file = _SEED_DIR / f"mock_trends_{snapshot_date.isoformat()}.json"
        if dated_file.exists():
            with dated_file.open(encoding="utf-8") as fh:
                return json.load(fh)
    with _MOCK_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def _parse_meta(raw_meta: dict, scenario: str) -> TrendSnapshotMeta:
    from app.contracts.trends import SourceRef

    return TrendSnapshotMeta(
        sources=[
            SourceRef(
                name=s["name"],
                url=s["url"],
                retrieved_at=date.fromisoformat(s["retrieved_at"]),
            )
            for s in raw_meta["sources"]
        ],
        snapshot_date=date.fromisoformat(raw_meta["snapshot_date"]),
        scenario=scenario,  # type: ignore[arg-type]
        is_estimate=raw_meta.get("is_estimate", True),
        weights=raw_meta.get("weights", {"research_velocity": 0.6, "labor_decay": 0.4}),
        labor_decay_is_static=raw_meta.get("labor_decay_is_static", True),
        available_snapshots=[
            date.fromisoformat(d) for d in raw_meta.get("available_snapshots", [])
        ],
        data_provenance_note=raw_meta.get("data_provenance_note"),
    )


def _parse_items(raw_items: list[dict], scenario: str) -> list[SkillVelocity]:
    items = []
    for item in raw_items:
        items.append(
            SkillVelocity(
                skill_id=item["skill_id"],
                skill_label=item["skill_label"],
                research_velocity=item["research_velocity"],
                labor_decay=item["labor_decay"],
                labor_decay_source_note=item["labor_decay_source_note"],
                automation_exposure=item["automation_exposure"],
                velocity_moderate=item["velocity_moderate"],
                velocity_fast=item["velocity_fast"],
                direction_moderate=item["direction_moderate"],  # type: ignore[arg-type]
                direction_fast=item["direction_fast"],  # type: ignore[arg-type]
            )
        )
    return items


def snapshot(scenario: str, snapshot_date: date | None = None) -> TrendSnapshotResponse:
    """Return a mock TrendSnapshotResponse for the given scenario and date."""
    if snapshot_date is None:
        snapshot_date = AVAILABLE_MOCK_DATES[-1]

    raw = _load_raw(snapshot_date)
    meta = _parse_meta(raw["meta"], scenario)
    meta.available_snapshots = list(AVAILABLE_MOCK_DATES)
    meta.snapshot_date = snapshot_date
    items = _parse_items(raw["items"], scenario)
    return TrendSnapshotResponse(meta=meta, items=items)
