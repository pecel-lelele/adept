"""Platform overview for the public home page (Core, M4).

Every figure is computed from the data the app itself uses: the latest trend snapshot (F2),
the scenario outlooks (F3), the role taxonomy and course catalogue (F4, F5) and the SDG links
(F6). Nothing is typed in by hand. Cached briefly because the home page is public.
"""

from __future__ import annotations

import threading
import time

from app.contracts.common import (
    OverviewRole,
    OverviewSkill,
    PlatformOverview,
    RecommendationMeta,
    Source,
)
from app.contracts.trends import SkillVelocity

CACHE_TTL_S = 60.0
_lock = threading.Lock()
_cached: tuple[float, PlatformOverview] | None = None


def _skill(item: SkillVelocity) -> OverviewSkill:
    return OverviewSkill(
        skill_id=item.skill_id,
        label=item.skill_label,
        velocity=round(item.velocity_moderate, 3),
        direction=item.direction_moderate,
    )


def build() -> PlatformOverview:
    from app.features.pathway import data as pathway_data
    from app.features.profile import service as profile_service
    from app.features.scenarios import service as scenarios_service
    from app.features.sdg import service as sdg_service
    from app.features.trends import service as trends_service

    snap = trends_service.get_snapshot(None, "moderate")
    items = sorted(snap.items, key=lambda i: i.velocity_moderate, reverse=True)
    count = {
        d: sum(1 for i in items if i.direction_moderate == d)
        for d in ("rising", "stable", "declining")
    }

    labels = pathway_data.role_labels()
    role_ids = pathway_data.target_role_ids()
    outlooks = [o for o in scenarios_service.get_outlook(None).outlooks if o.scenario == "moderate"]
    top_roles = [
        OverviewRole(
            role_id=o.role_id,
            label=labels.get(o.role_id, o.role_id),
            outlook=o.outlook,
            low=o.low,
            high=o.high,
        )
        for o in sorted(outlooks, key=lambda o: o.outlook, reverse=True)[:3]
    ]

    courses = pathway_data.catalogue()
    goals = {t.goal for rid in role_ids for t in sdg_service.role_badges(rid)}

    return PlatformOverview(
        skills_in_bank=len(profile_service.skill_catalogue().skills),
        skills_tracked=len(items),
        rising=count["rising"],
        stable=count["stable"],
        declining=count["declining"],
        top_rising=[_skill(i) for i in items if i.direction_moderate == "rising"][:3],
        top_declining=[_skill(i) for i in reversed(items) if i.direction_moderate == "declining"][
            :2
        ],
        roles=len(role_ids),
        top_roles=top_roles,
        courses=len(courses),
        free_courses=sum(1 for c in courses if c.cost_myr == 0),
        hrd_claimable_courses=sum(1 for c in courses if c.hrd_claimable),
        providers=len({c.provider for c in courses}),
        sdg_goals_linked=len(goals),
        meta=RecommendationMeta(
            sources=[
                Source(name=s.name, url=s.url, retrieved_at=s.retrieved_at)
                for s in snap.meta.sources
            ],
            snapshot_date=snap.meta.snapshot_date,
            scenario="moderate",
            is_estimate=True,
        ),
    )


def get() -> PlatformOverview:
    global _cached
    with _lock:
        if _cached and time.monotonic() - _cached[0] < CACHE_TTL_S:
            return _cached[1]
    result = build()
    with _lock:
        _cached = (time.monotonic(), result)
    return result


def reset() -> None:
    global _cached
    with _lock:
        _cached = None
