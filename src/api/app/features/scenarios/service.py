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

import math
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

# Bug 3 fix: decouple uncertainty width from signal magnitude.
# A nonzero base ensures widen > 0 whenever coverage < 1, even when the signal is near zero.
BASE_UNCERTAINTY: float = 0.10
# Below this coverage share the evidence is too thin to trust the numeric range;
# the flag ``insufficient_evidence`` is set on the RoleOutlook so the UI can surface it.
MIN_COVERAGE_THRESHOLD: float = 0.20


def _meta(snap: TrendSnapshotResponse, scenario: ScenarioId) -> RecommendationMeta:
    return RecommendationMeta(
        sources=[
            Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at) for s in snap.meta.sources
        ],
        snapshot_date=snap.meta.snapshot_date,
        scenario=scenario,
        is_estimate=True,
        served_from=snap.meta.served_from,
        is_fallback=snap.meta.is_fallback,
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


def enforce_fast_magnitude(moderate: float, fast: float) -> float:
    """Bug 2 fix: at the role-aggregation level, |fast deviation| must be >= |moderate deviation|.

    Per-skill, scenario_fast() always preserves sign and direction.  At the role level,
    importance-weighted sums of mixed-exposure skills can partially cancel, making the
    aggregate fast signal *less* extreme than moderate.  This guard restores the invariant
    by flooring |fast| to |moderate| when they share the same direction, without ever
    flipping the sign of the fast signal.
    """
    if abs(fast) >= abs(moderate):
        return fast  # invariant already satisfied
    # Only apply the floor when both signals have the same direction (or fast is 0).
    # Opposite-sign signals indicate contradictory skill mixes; report them as-is and let
    # the uncertainty range carry the ambiguity.
    same_direction = (moderate >= 0 and fast >= 0) or (moderate <= 0 and fast <= 0)
    if same_direction:
        return math.copysign(abs(moderate), moderate)
    return fast


def outlook_range(signals: list[float], latest: float, coverage: float) -> tuple[float, float]:
    """Bug 3 fix: uncertainty width is decoupled from signal magnitude.

    Old formula: ``widen = (1 - coverage) * abs(clip(latest))`` collapses to 0 whenever
    the signal is near 0 regardless of coverage, giving a false point estimate.
    New formula adds BASE_UNCERTAINTY so low-coverage roles always show a nonzero range.
    """
    widen = (1.0 - coverage) * (abs(clip(latest)) + BASE_UNCERTAINTY)
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

        # Bug 2 fix: compute both scenarios before emitting any RoleOutlook so we can
        # enforce the fast-magnitude invariant at the role-aggregation level.
        signals: dict[ScenarioId, float | None] = {}
        coverages: dict[ScenarioId, float] = {}
        for sid in SCENARIO_IDS:
            latest_v = history[sid][-1]
            sig, cov = role_signal(reqs, latest_v)
            signals[sid] = sig
            coverages[sid] = cov

        # Apply invariant: |fast| >= |moderate| (same direction).
        if signals["moderate"] is not None and signals["fast"] is not None:
            signals["fast"] = enforce_fast_magnitude(signals["moderate"], signals["fast"])

        for sid in SCENARIO_IDS:
            signal = signals[sid]
            coverage = coverages[sid]
            if signal is None:
                continue
            past = [s for s in (role_signal(reqs, v)[0] for v in history[sid]) if s is not None]
            low, high = outlook_range(past or [signal], signal, coverage)
            outlook_val = round(1.0 + clip(signal), 3)
            # Guarantee low <= outlook_val <= high even after enforce_fast_magnitude may have
            # pushed the signal beyond the stored historical range.
            low = min(low, outlook_val)
            high = max(high, outlook_val)
            outlooks.append(
                RoleOutlook(
                    role_id=rid,
                    scenario=sid,
                    outlook=outlook_val,
                    low=low,
                    high=high,
                    insufficient_evidence=coverage < MIN_COVERAGE_THRESHOLD,
                )
            )
    if role_id is not None and not outlooks:
        raise NotFoundError(f"No trend coverage for role {role_id}")
    return OutlookResponse(outlooks=outlooks, meta=_meta(latest, "moderate"))
