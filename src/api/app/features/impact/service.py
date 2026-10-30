"""Impact evidence (F8): numbers computed on request from production code.

Synthetic personas are run through the real ranking and pathway functions in process (no HTTP).
Nothing is stored or hard-coded: change the catalogue, the trend snapshot or the engines and
every figure changes with them. Dates come from the data, never from the clock.
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.contracts.common import RecommendationMeta, Source
from app.contracts.impact import (
    CatalogueCoverage,
    CountBucket,
    EvidenceItem,
    FairnessEvidence,
    ImpactAggregate,
    ImpactSummary,
    PathwayImpact,
    PersonaImpact,
)
from app.contracts.labour import MalaysiaLabourContext
from app.contracts.pathway import Course, Pathway
from app.contracts.profile import Profile, Segment, UserSkill
from app.core import refdata
from app.core.config import REPO_ROOT, get_settings
from app.core.errors import AppError
from app.core.fairness import PROTECTED_TERMS
from app.core.seed import SEED_DIR
from app.features.matching import repository as matching_repository
from app.features.matching.scoring import MatchProfile, Weights, rank_roles
from app.features.matching.trend_port import TrendSnapshot, fetch_snapshot
from app.features.pathway import data as pathway_data
from app.features.pathway import engine
from app.features.pathway import service as pathway_service
from app.features.sdg import repository as sdg_repository
from app.features.trends import labour as trends_labour

VERIFIED_WINDOW_DAYS = 30
TOP_K = 5
DEMO_PROFILES = REPO_ROOT / "docs" / "demo-cvs" / "profiles.json"


def persona_note(count: int) -> str:
    return (
        f"Computed on {count} synthetic personas from the live catalogue and trend snapshot; "
        "no human trials."
    )


# Names and segments swapped in the counterfactual check. All are synthetic.
SWAP_NAMES = ("Aisyah binti Ahmad", "Tan Wei Jie", "Ravi Kumar", "Siti Nurhaliza", "John Smith")
SWAP_SEGMENTS: tuple[Segment, ...] = ("working", "graduate", "switcher")


@dataclass(frozen=True)
class Persona:
    persona_id: str
    source: str
    segment: Segment
    interests: tuple[str, ...]
    skills: dict[str, int]
    hours_per_week: float
    budget_myr: float
    hrd_eligible: bool


# --- personas ---------------------------------------------------------------------------


def _clamp(level: int) -> int:
    return max(1, min(5, level))


def load_personas() -> list[Persona]:
    out: list[Persona] = []
    if DEMO_PROFILES.exists():
        for p in json.loads(DEMO_PROFILES.read_text(encoding="utf-8")):
            out.append(
                Persona(
                    persona_id=p["user_id"],
                    source="docs/demo-cvs/profiles.json",
                    segment=p["segment"],
                    interests=tuple(p.get("interests", [])),
                    skills={s["skill_id"]: _clamp(int(s["level"])) for s in p["skills"]},
                    hours_per_week=float(p["hours_per_week"]),
                    budget_myr=float(p["budget_myr"]),
                    hrd_eligible=bool(p["hrd_eligible"]),
                )
            )
    return [p for p in out if p.skills]


def _match_profile(p: Persona) -> MatchProfile:
    return MatchProfile(
        skills={k: float(v) for k, v in p.skills.items()}, interests=frozenset(p.interests)
    )


# --- pure metrics -----------------------------------------------------------------------


def _share(part: float, whole: float) -> float:
    return round(part / whole, 4) if whole > 0 else 0.0


def path_courses(pathway: Pathway) -> list[Course]:
    """Distinct courses booked by the path, in order."""
    seen: dict[str, Course] = {}
    for step in pathway.steps:
        for course in step.courses:
            seen.setdefault(course.id, course)
    return list(seen.values())


def _target_key(target: str) -> tuple[float, ...]:
    return tuple(float(p) if p.isdigit() else 0.0 for p in target.replace("-", ".").split("."))


def pathway_metrics(pathway: Pathway, scenario: str, role_label: str) -> PathwayImpact:
    courses = path_courses(pathway)
    hours = sum(c.hours for c in courses)
    free = [c for c in courses if c.cost_myr == 0]
    hrd = [c for c in courses if c.hrd_claimable]
    targets = sorted({t.target for s in pathway.steps for t in s.sdg_targets}, key=_target_key)
    return PathwayImpact(
        scenario=scenario,  # type: ignore[arg-type]
        top_role_id=pathway.role_id,
        top_role_label=role_label,
        course_count=len(courses),
        total_hours=round(hours, 1),
        free_course_share=_share(len(free), len(courses)),
        free_hours_share=_share(sum(c.hours for c in free), hours),
        hrd_course_share=_share(len(hrd), len(courses)),
        hrd_hours_share=_share(sum(c.hours for c in hrd), hours),
        sdg_target_count=len(targets),
        sdg_targets=targets,
    )


def public_evidence() -> list[EvidenceItem]:
    """Figures quoted from fetched public pages; served as data, never typed into components."""
    path = SEED_DIR / "impact" / "public_evidence.json"
    return [EvidenceItem.model_validate(e) for e in json.loads(path.read_text(encoding="utf-8"))]


def labour_context() -> MalaysiaLabourContext | None:
    try:
        return trends_labour.current()
    except Exception:  # noqa: BLE001 - omit rather than show a placeholder
        return None


def _median(values: Sequence[float]) -> float:
    return round(float(statistics.median(values)), 4) if values else 0.0


def aggregate(personas: Sequence[PersonaImpact], scenario: str) -> ImpactAggregate:
    paths: list[PathwayImpact] = [getattr(p, scenario) for p in personas]
    return ImpactAggregate(
        scenario=scenario,  # type: ignore[arg-type]
        persona_count=len(paths),
        median_free_course_share=_median([x.free_course_share for x in paths]),
        median_free_hours_share=_median([x.free_hours_share for x in paths]),
        median_hrd_course_share=_median([x.hrd_course_share for x in paths]),
        median_total_hours=_median([x.total_hours for x in paths]),
        median_sdg_target_count=_median([float(x.sdg_target_count) for x in paths]),
        median_top5_changed=_median([float(p.top5_changed) for p in personas]),
    )


# --- production runs --------------------------------------------------------------------


def _ranked(p: Persona, snap: TrendSnapshot) -> list[str]:
    ranked = rank_roles(
        _match_profile(p),
        matching_repository.load_roles(),
        snap.velocities,
        Weights(),
        reference_velocities=snap.reference_velocities,
    )
    return [r.role_id for r in ranked]


def _persona_impact(p: Persona, snaps: dict[str, TrendSnapshot]) -> PersonaImpact:
    ranks = {s: _ranked(p, snaps[s]) for s in ("moderate", "fast")}
    learner = engine.Learner(dict(p.skills), p.hours_per_week, p.budget_myr, p.hrd_eligible)
    labels = pathway_data.role_labels()
    paths: dict[str, PathwayImpact] = {}
    for scenario in ("moderate", "fast"):
        top = ranks[scenario][0]
        plan = pathway_service.build_pathway(
            learner, top, scenario, snapshot_date=snaps[scenario].snapshot_date
        )  # type: ignore[arg-type]
        paths[scenario] = pathway_metrics(plan, scenario, labels.get(top, top))
    return PersonaImpact(
        persona_id=p.persona_id,
        source=p.source,
        skill_count=len(p.skills),
        hours_per_week=p.hours_per_week,
        hrd_eligible=p.hrd_eligible,
        moderate=paths["moderate"],
        fast=paths["fast"],
        top5_changed=len(set(ranks["moderate"][:TOP_K]) - set(ranks["fast"][:TOP_K])),
        top_role_changed=ranks["moderate"][0] != ranks["fast"][0],
    )


def catalogue_coverage() -> CatalogueCoverage:
    rows = refdata.rows("courses", "courses", non_retired_only=True, order_by_id=True)
    if not rows:
        raise AppError("No catalogue is available.", status_code=503, code="catalogue_unavailable")
    as_of = max(date.fromisoformat(r["verified_at"]) for r in rows)
    since = as_of - timedelta(days=VERIFIED_WINDOW_DAYS)
    recent = sum(1 for r in rows if r["verified_at"] >= since.isoformat())
    free = [r for r in rows if float(r["cost_myr"]) == 0]
    roles = {r["id"] for r in refdata.rows("taxonomy", "roles")}
    skills = pathway_data.skill_labels()
    targets = {r["id"] for r in refdata.rows("sdg", "sdg_targets")}
    role_links = {
        (r["role_id"], r["sdg_target_id"])
        for r in refdata.rows("sdg", "role_sdg_map")
        if r["role_id"] in roles and r["sdg_target_id"] in targets
    }
    linked_targets = {target for _, target in role_links} | {
        r["sdg_target_id"]
        for r in refdata.rows("sdg", "skill_sdg_map")
        if r["skill_id"] in skills and r["sdg_target_id"] in targets
    }

    def buckets(counter: Counter[str]) -> list[CountBucket]:
        return [CountBucket(key=k, count=n) for k, n in sorted(counter.items())]

    return CatalogueCoverage(
        course_count=len(rows),
        role_count=len(roles),
        target_role_count=len(pathway_data.target_role_ids()),
        skill_count=len(skills),
        free_course_count=len(free),
        free_course_share=_share(len(free), len(rows)),
        free_hours=round(sum(float(r["hours"]) for r in free), 1),
        sdg_target_count=len(linked_targets),
        role_sdg_link_count=len(role_links),
        by_language=buckets(Counter((r.get("language") or "unspecified") for r in rows)),
        by_provider_type=buckets(Counter((r.get("provider_type") or "unknown") for r in rows)),
        verified_recent_share=_share(recent, len(rows)),
        verified_window_days=VERIFIED_WINDOW_DAYS,
        verified_since=since,
        as_of=as_of,
    )


def _swapped_profile(p: Persona, name: str, segment: Segment) -> Profile:
    return Profile(
        user_id=p.persona_id,
        display_name=name,
        segment=segment,
        interests=list(p.interests),
        hours_per_week=int(p.hours_per_week),
        budget_myr=p.budget_myr,
        hrd_eligible=p.hrd_eligible,
        skills=[UserSkill(skill_id=k, level=v, source="confirmed") for k, v in p.skills.items()],
    )


def fairness_evidence(personas: Sequence[Persona], snap: TrendSnapshot) -> FairnessEvidence:
    """Swap name and segment on each persona's profile and re-rank through the production
    profile-to-matching boundary and scorer; report the largest position change of any role."""
    from app.features.guardrails import service as guardrails_service
    from app.main import app

    roles = matching_repository.load_roles()

    def positions(profile: Profile) -> dict[str, int]:
        levels = {s.skill_id: s.level for s in profile.skills}
        ranked = rank_roles(
            matching_repository.profile_to_match(profile, levels),
            roles,
            snap.velocities,
            Weights(),
            reference_velocities=snap.reference_velocities,
        )
        return {r.role_id: i for i, r in enumerate(ranked)}

    worst = variants = 0
    for p in personas:
        base = positions(_swapped_profile(p, "baseline", p.segment))
        for name in SWAP_NAMES:
            for segment in SWAP_SEGMENTS:
                now = positions(_swapped_profile(p, name, segment))
                variants += 1
                worst = max(worst, max(abs(now[r] - base[r]) for r in base))
    report = guardrails_service.get_fairness(app)
    return FairnessEvidence(
        variants_tested=variants,
        personas_tested=len(personas),
        max_rank_change=worst,
        guardrail_report_passed=report.passed,
        api_inputs_checked=report.api_inputs_checked,
        protected_inputs_found=report.protected_inputs_found,
        method=(
            f"Each persona's profile is re-ranked with {len(SWAP_NAMES)} names x "
            f"{len(SWAP_SEGMENTS)} segments swapped; {len(PROTECTED_TERMS)} protected terms "
            "are screened out of every API input."
        ),
    )


def _meta(snap: TrendSnapshot, evidence: Sequence[EvidenceItem]) -> RecommendationMeta:
    courses = pathway_data.catalogue()
    repo = "https://github.com/pecel-lelele/adept/blob/main"
    sources = [
        Source(
            name="Adept course catalogue (retrieved at its oldest verification date)",
            url=f"{repo}/src/data/seed/courses/courses.csv",
            retrieved_at=min(c.verified_at for c in courses),
        ),
        pathway_data.taxonomy_source(),
        sdg_repository.un_source(),
        sdg_repository.mapping_source(),
        *snap.sources,
        Source(
            name="Synthetic personas (docs/demo-cvs)",
            url=f"{repo}/docs/demo-cvs/profiles.json",
            retrieved_at=date.fromisoformat("2026-10-30"),  # files inspected for this entry
        ),
    ]
    sources += [Source(name=e.publisher, url=e.url, retrieved_at=e.retrieved_at) for e in evidence]
    unique = {(x.name, x.url): x for x in sources}
    return RecommendationMeta(
        sources=list(unique.values()),
        snapshot_date=snap.snapshot_date,
        scenario="moderate",
        is_estimate=True,
        served_from=snap.served_from,
        is_fallback=snap.is_fallback,
        observed_from=snap.observed_from,
        observed_to=snap.observed_to,
    )


FORMULAS: dict[str, str] = {
    "free_share": "free courses / courses in the path, cost_myr == 0, per persona; median over "
    "personas",
    "free_hours_share": "hours of free courses / hours of all courses in the path",
    "hrd_share": "courses with hrd_claimable / courses in the path (eligibility is not approved "
    "funding)",
    "hours": "sum of hours of the distinct courses in the pathway engine's plan; median over "
    "personas",
    "sdg": "distinct SDG targets on the steps of the path (skill to target mapping)",
    "scenario": "roles in the Moderate top 5 that are not in the Fast top 5, same profile, same "
    "scorer",
    "fairness": "largest change in any role's rank when name and segment are swapped on a "
    "persona's profile, through the production profile-to-matching boundary and scorer",
    "verified": "courses verified within the window before the newest catalogue verification / all "
    "non-retired courses",
}


def compute_summary() -> ImpactSummary:
    moderate = fetch_snapshot("moderate")
    snaps: dict[str, TrendSnapshot] = {
        "moderate": moderate,
        "fast": fetch_snapshot("fast", moderate.snapshot_date),
    }
    personas = load_personas()
    if not personas:
        raise AppError(
            "No synthetic personas are available.", status_code=503, code="personas_unavailable"
        )
    evidence = public_evidence()
    impacts = [_persona_impact(p, snaps) for p in personas]
    snap = snaps["moderate"]
    return ImpactSummary(
        personas=impacts,
        aggregates=[aggregate(impacts, "moderate"), aggregate(impacts, "fast")],
        catalogue=catalogue_coverage(),
        fairness=fairness_evidence(personas, snap),
        public_evidence=evidence,
        labour_context=labour_context(),
        formulas=FORMULAS,
        persona_note=persona_note(len(personas)),
        meta=_meta(snap, evidence),
    )


_summary_lock = threading.Lock()
_summary_cache: tuple[float, ImpactSummary] | None = None


def get_summary() -> ImpactSummary:
    """Recomputed from the live catalogue, trend snapshot and engines.

    The result is reused for at most IMPACT_SUMMARY_TTL_S seconds.

    The public page re-ranks every synthetic persona, so a short memo stops repeated anonymous
    requests from redoing that work while a data refresh still shows within the TTL.
    Failures are never cached.
    """
    global _summary_cache
    ttl = get_settings().impact_summary_ttl_s
    now = time.monotonic()
    cached = _summary_cache
    if cached and now - cached[0] < ttl:
        return cached[1]
    with _summary_lock:
        cached = _summary_cache
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1]
        summary = compute_summary()
        _summary_cache = (time.monotonic(), summary)
        return summary


def clear_summary_cache() -> None:
    global _summary_cache
    _summary_cache = None
