"""Scenarios and role outlooks (F3), computed from the dated trend snapshots (F2).

Nothing is hard-coded. Method (documented in docs/decisions.md):

- Scenario parameters come from the trend pipeline (`src/pipelines/trends/score.py`):
  moderate = measured velocity, fast = velocity amplified by k = 1.5 according to each
  skill's automation exposure. `adoption_rate` = mean automation exposure of the tracked
  skills (moderate) and the same exposure amplified by (1 + k), capped at 1 (fast).
- Role outlook = 1 + importance-weighted velocity of the role's required skills in the
  latest snapshot, clipped to the pathway engine's growth band [-0.5, +1.0] so the index
  stays a valid demand index (0.5 = half today's demand, 1.0 = today's, 2.0 = double).
  Low / high = the lowest / highest value across every stored snapshot, widened by the share
  of required skills the snapshot does not cover, and kept inside the same band. Always an
  estimate.
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.scenarios import OutlookResponse, RoleOutlook, Scenario, ScenarioListResponse
from app.contracts.trends import TrendSnapshotResponse
from app.core.errors import NotFoundError
from app.features.scenarios import repository

FAST_K = 1.5  # src/pipelines/trends/score.py: K
GROWTH_CLIP = (-0.5, 1.0)  # same band as app.features.pathway.engine.GROWTH_CLIP
SCENARIO_IDS: tuple[ScenarioId, ...] = ("moderate", "fast")
_TEXT: dict[ScenarioId, tuple[str, str]] = {
    "moderate": (
        "Moderate AI disruption",
        "Skill demand moves at the pace measured in the latest research and labour signals.",
    ),
    "fast": (
        "Fast AI disruption",
        "The same signals amplified for automation exposure: exposed skills decline faster, "
        "AI-complementary skills rise faster.",
    ),
}


def _meta(snap: TrendSnapshotResponse, scenario: ScenarioId) -> RecommendationMeta:
    return RecommendationMeta(
        sources=[
            Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
        ],
        snapshot_date=snap.meta.snapshot_date,
        scenario=scenario,
        is_estimate=True,
        observed_from=snap.meta.observed_from,
        observed_to=snap.meta.observed_to,
    )


def adoption_rate(exposures: list[float], scenario: ScenarioId) -> float:
    if not exposures:
        return 0.0
    factor = 1.0 if scenario == "moderate" else 1.0 + FAST_K
    return round(min(1.0, sum(min(1.0, e * factor) for e in exposures) / len(exposures)), 3)


def role_signal(
    requirements: list[tuple[str, float]], velocities: dict[str, float]
) -> tuple[float | None, float]:
    """Importance-weighted velocity of the covered skills, and the covered weight share."""
    total = sum(w for _, w in requirements)
    covered = [(s, w) for s, w in requirements if s in velocities]
    weight = sum(w for _, w in covered)
    if total <= 0 or weight <= 0:
        return None, 0.0
    return sum(w * velocities[s] for s, w in covered) / weight, weight / total


def clip(signal: float) -> float:
    lo, hi = GROWTH_CLIP
    return max(lo, min(hi, signal))


def outlook_range(signals: list[float], latest: float, coverage: float) -> tuple[float, float]:
    widen = (1.0 - coverage) * abs(clip(latest))
    low = clip(min(clip(s) for s in signals) - widen)
    high = clip(max(clip(s) for s in signals) + widen)
    return round(1.0 + low, 3), round(1.0 + high, 3)


def list_scenarios() -> ScenarioListResponse:
    scenarios: list[Scenario] = []
    latest = repository.snapshot("moderate")
    exposures = [item.automation_exposure for item in latest.items]
    for sid in SCENARIO_IDS:
        label, description = _TEXT[sid]
        scenarios.append(
            Scenario(
                id=sid,
                label=label,
                adoption_rate=adoption_rate(exposures, sid),
                description=description,
            )
        )
    return ScenarioListResponse(scenarios=scenarios, meta=_meta(latest, "moderate"))


def get_outlook(role_id: str | None, snapshot_date: date | None = None) -> OutlookResponse:
    """Outlook per role and scenario as of the latest snapshot, or as of ``snapshot_date``.

    With a date, only snapshots up to and including it are used, so a historical match page
    shows the outlook that was knowable then and cites that snapshot.
    """
    roles = repository.target_role_ids()
    if role_id is not None:
        if role_id not in roles:
            raise NotFoundError(f"No outlook for role {role_id}")
        roles = [role_id]
    snaps = repository.history()  # oldest first; the last one is the latest
    if snapshot_date is not None:
        snaps = [s for s in snaps if s.meta.snapshot_date <= snapshot_date]
        if not snaps or snaps[-1].meta.snapshot_date != snapshot_date:
            raise NotFoundError(f"No trend snapshot for {snapshot_date.isoformat()}")
    latest = snaps[-1]
    history: dict[ScenarioId, list[dict[str, float]]] = {
        sid: [{i.skill_id: float(getattr(i, f"velocity_{sid}")) for i in s.items} for s in snaps]
        for sid in SCENARIO_IDS
    }
    outlooks: list[RoleOutlook] = []
    for rid in roles:
        reqs = [(r.skill_id, r.importance) for r in repository.role_requirements(rid)]
        for sid in SCENARIO_IDS:
            latest_v = history[sid][-1]
            signal, coverage = role_signal(reqs, latest_v)
            if signal is None:
                continue
            past = [s for s in (role_signal(reqs, v)[0] for v in history[sid]) if s is not None]
            low, high = outlook_range(past or [signal], signal, coverage)
            outlooks.append(
                RoleOutlook(
                    role_id=rid,
                    scenario=sid,
                    outlook=round(1.0 + clip(signal), 3),
                    low=low,
                    high=high,
                )
            )
    if role_id is not None and not outlooks:
        raise NotFoundError(f"No trend coverage for role {role_id}")
    return OutlookResponse(outlooks=outlooks, meta=_meta(latest, "moderate"))
