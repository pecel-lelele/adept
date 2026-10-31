"""Live openings for a role, how close the learner is to them, and the certifications that
follow the plan. Reads the learner's effective skills and plan through F5's service, so the
numbers agree with the plan page. Never ranks or filters people: openings are information,
applications happen on the employer's own site.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.jobs import (
    Certification,
    CertificationList,
    JobBoardPage,
    JobOpening,
    OpeningPlaceCounts,
    OpeningsSummary,
    Payer,
    RoleOpeningCount,
    RoleOpenings,
    SkillAsk,
    SkillDemand,
)
from app.contracts.pathway import Pathway
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError, ProfileRequiredError
from app.core.logging import get_logger
from app.features.jobs import fit, repository
from app.features.jobs.repository import Posting
from app.features.pathway import data as pathway_data
from app.features.pathway import service as pathway_service

log = get_logger("app.jobs")

PIPELINE_URL = "https://github.com/pecel-lelele/adept/blob/main/src/pipelines/jobs/boards.py"


# --- learner context ---------------------------------------------------------------------------


class Context:
    """The learner's effective levels and the plan towards one role (empty when unavailable)."""

    def __init__(
        self,
        have: Mapping[str, int] | None,
        plan: Pathway | None,
        required: Mapping[str, int],
    ) -> None:
        self.have = have
        self.plan = plan
        self.required = required
        self.plan_levels: dict[str, int] = (
            {s.skill_id: s.reaches_level for s in plan.steps} if plan else {}
        )

    def status(self, skill_id: str) -> str:
        return fit.status(skill_id, self.have, self.plan_levels, self.required)


def _context(user: CurrentUser, role_id: str, scenario: ScenarioId) -> Context:
    required = {r.skill_id: r.required_level for r in pathway_data.requirements(role_id)}
    try:
        have = pathway_service.learner_for(user).skill_levels
    except ProfileRequiredError:
        return Context(None, None, required)
    plan: Pathway | None = None
    try:
        saved = pathway_service.get_saved_plan(user)
        if saved and saved.role_id == role_id and saved.scenario == scenario:
            plan = saved.pathway
        else:
            plan = pathway_service.get_pathway(user, role_id, scenario)
    except (NotFoundError, AppError) as exc:
        log.info("no plan for %s towards %s: %s", user.id, role_id, exc)
    return Context(have, plan, required)


# --- shared builders ---------------------------------------------------------------------------


def _unavailable() -> AppError:
    return AppError(
        "Job openings data is unavailable right now.", status_code=503, code="jobs_unavailable"
    )


def _feed_date() -> date | None:
    """When the openings feed was last actually read: the pipeline's fetch date, else the
    newest stored observation. Never the request date: an empty result must not look fresh."""
    fetched = repository.fetch_log().get("fetched_on")
    if isinstance(fetched, str):
        try:
            return date.fromisoformat(fetched[:10])
        except ValueError:
            pass
    return repository.observation_date()


def _meta(rows: Sequence[Posting], scenario: ScenarioId) -> RecommendationMeta:
    """One source per employer feed or job board, dated by the last time it was read."""
    latest: dict[tuple[str, str], tuple[date, str]] = {}
    for p in rows:
        name = (
            f"{p.employer} careers ({p.source_name})"
            if p.source in ("greenhouse", "lever", "ashby", "smartrecruiters", "workday", "jibe")
            else p.source_name
        )
        key = (name, p.api_url)
        if key not in latest or p.last_seen > latest[key][0]:
            latest[key] = (p.last_seen, p.api_url)
    sources = [
        Source(name=name, url=url, retrieved_at=day)
        for (name, url), (day, _) in sorted(latest.items())
    ]
    fetched = max((s.retrieved_at for s in sources), default=None) or _feed_date()
    if fetched is None:
        raise AppError(
            "No dated job observations are available yet.", status_code=503, code="jobs_no_data"
        )
    if not sources:
        sources = [
            Source(name="Adept job openings pipeline", url=PIPELINE_URL, retrieved_at=fetched)
        ]
    # Role assignment and skill extraction from ad text are estimates; the openings are real.
    return RecommendationMeta(sources=sources, snapshot_date=fetched, scenario=scenario)


def _places(rows: Sequence[Posting]) -> OpeningPlaceCounts:
    states = Counter(repository.relevance(p) for p in rows)
    return OpeningPlaceCounts(
        in_malaysia=states["in_malaysia"],
        remote_explicit_my=states["remote_explicit_my"],
        remote_assumed_worldwide=states["remote_assumed_worldwide"],
    )


def _opening(p: Posting, ctx: Context | None, labels: Mapping[str, str]) -> JobOpening:
    statuses = [ctx.status(s) if ctx else "not_rated" for s in p.skill_ids]
    now, after = fit.shares(statuses)
    return JobOpening(
        id=p.id,
        title=p.title,
        employer=p.employer,
        location=p.location,
        work_mode=p.work_mode,  # type: ignore[arg-type]
        remote_scope=p.remote_scope,
        malaysia_relevance=repository.relevance(p),  # type: ignore[arg-type]
        employment_type=p.employment_type,
        seniority=p.seniority,  # type: ignore[arg-type]
        url=p.url,
        source_name=p.source_name,
        posted_at=p.posted_at,
        first_seen=p.first_seen,
        last_seen=p.last_seen,
        is_stale=p.stale,
        role_method=p.role_method or "title",  # type: ignore[arg-type]
        skills=[
            SkillAsk(skill_id=s, label=labels.get(s, s), status=st)  # type: ignore[arg-type]
            for s, st in zip(p.skill_ids, statuses, strict=True)
        ],
        cert_ids=list(p.cert_ids),
        match_now=now,
        match_after_plan=after,
    )


def _counts(rows: Sequence[Posting]) -> list[RoleOpeningCount]:
    labels = pathway_data.role_labels()
    by_role: dict[str, list[Posting]] = {}
    for p in rows:
        if p.role_id:
            by_role.setdefault(p.role_id, []).append(p)
    return [
        RoleOpeningCount(
            role_id=rid,
            role_label=labels.get(rid, rid),
            open_count=len(ps),
            employer_count=len({p.employer for p in ps}),
            remote_count=sum(p.work_mode == "remote" for p in ps),
            places=_places(ps),
        )
        for rid, ps in sorted(by_role.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]


# --- endpoints ---------------------------------------------------------------------------------


def summary(scenario: ScenarioId = "moderate") -> OpeningsSummary:
    rows = repository.openings()
    counts = _counts(rows)
    assigned = [p for p in rows if p.role_id]
    meta = _meta(rows, scenario)
    return OpeningsSummary(
        roles=counts,
        total_open=len(assigned),
        employer_count=len({p.employer for p in assigned}),
        fetched_on=meta.snapshot_date if rows else None,
        meta=meta,
    )


def role_openings(
    user: CurrentUser,
    role_id: str,
    scenario: ScenarioId = "moderate",
    limit: int = 8,
    malaysia_focus: bool = False,
) -> RoleOpenings:
    labels = pathway_data.role_labels()
    if role_id not in labels:
        raise NotFoundError(f"Unknown role {role_id}")
    read = repository.malaysia_relevant_openings if malaysia_focus else repository.openings
    rows = [p for p in read() if p.role_id == role_id]
    ctx = _context(user, role_id, scenario)
    skill_labels = pathway_data.skill_labels()
    cards = [_opening(p, ctx, skill_labels) for p in rows]
    # Possibly closed ads stay visible, labelled and after every open one; stats ignore them.
    stale_cards = [
        _opening(p, ctx, skill_labels)
        for p in read(include_stale=True)
        if p.stale and p.role_id == role_id
    ]
    # Closest first after the plan, then today, then newest; unrated ads last.
    cards.sort(
        key=lambda o: (
            o.match_after_plan is None,
            -(o.match_after_plan or 0),
            -(o.match_now or 0),
            -(o.posted_at or o.first_seen).toordinal(),
        )
    )
    rated = [o for o in cards if o.match_now is not None]
    top = fit.demand([p.skill_ids for p in rows])
    employers = Counter(p.employer for p in rows)
    meta = _meta(rows, scenario)
    return RoleOpenings(
        role_id=role_id,
        role_label=labels[role_id],
        open_count=len(rows),
        employer_count=len(employers),
        remote_count=sum(p.work_mode == "remote" for p in rows),
        places=_places(rows),
        employers=[e for e, _ in sorted(employers.items(), key=lambda kv: (-kv[1], kv[0]))[:8]],
        openings=(cards + stale_cards)[: max(1, min(limit, 50))],
        skill_demand=[
            SkillDemand(
                skill_id=s,
                label=skill_labels.get(s, s),
                openings=n,
                share=round(n / len(rows), 3),
                status=ctx.status(s),  # type: ignore[arg-type]
            )
            for s, n in top
        ],
        ready_threshold=fit.READY_SHARE,
        ready_now=sum(fit.within_reach(o.match_now) for o in rated),
        ready_after_plan=sum(fit.within_reach(o.match_after_plan) for o in rated),
        rated=len(rated),
        has_plan=ctx.plan is not None,
        fetched_on=meta.snapshot_date if rows else None,
        meta=meta,
    )


def board(
    user: CurrentUser,
    scenario: ScenarioId = "moderate",
    role_id: str | None = None,
    q: str = "",
    work_mode: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> JobBoardPage:
    listed = [p for p in repository.malaysia_relevant_openings(include_stale=True) if p.role_id]
    # Counts are open (fresh) ads only; the listing keeps stale ads last, labelled.
    fresh = [p for p in listed if not p.stale]
    counts = _counts(fresh)
    rows = listed
    if role_id:
        rows = [p for p in rows if p.role_id == role_id]
    if work_mode:
        rows = [p for p in rows if p.work_mode == work_mode]
    needle = q.strip().lower()
    if needle:
        rows = [
            p
            for p in rows
            if needle in p.title.lower()
            or needle in p.employer.lower()
            or needle in p.location.lower()
        ]
    ctx = _context(user, role_id, scenario) if role_id else None
    labels = pathway_data.skill_labels()
    start = (page - 1) * page_size
    return JobBoardPage(
        openings=[_opening(p, ctx, labels) for p in rows[start : start + page_size]],
        total=len(rows),
        page=page,
        page_size=page_size,
        places=_places(fresh),
        roles=counts,
        fetched_on=_meta(rows, scenario).snapshot_date if rows else None,
        meta=_meta(rows or listed or repository.malaysia_relevant_openings(), scenario),
    )


def certifications(
    user: CurrentUser, role_id: str, scenario: ScenarioId = "moderate", payer: Payer = "learner"
) -> CertificationList:
    labels = pathway_data.role_labels()
    if role_id not in labels:
        raise NotFoundError(f"Unknown role {role_id}")
    ctx = _context(user, role_id, scenario) if payer == "learner" else Context(None, None, {})
    required = {r.skill_id for r in pathway_data.requirements(role_id)}
    openings = [p for p in repository.openings() if p.role_id == role_id]
    skill_labels = pathway_data.skill_labels()
    plan_courses = (
        [(c.id, set(c.skill_ids)) for step in ctx.plan.steps for c in step.courses]
        if ctx.plan
        else []
    )
    out: list[Certification] = []
    for c in repository.certifications():
        overlap = required & set(c.skill_ids)
        if not overlap:
            continue
        out.append(
            Certification(
                id=c.id,
                name=c.name,
                issuer=c.issuer,
                exam_code=c.exam_code,
                url=c.url,
                level=c.level,  # type: ignore[arg-type]
                fee_amount=c.fee_amount,
                fee_currency=c.fee_currency,
                fee_myr=c.fee_myr,
                fee_note=c.fee_note,
                fee_source_url=c.fee_source_url,
                verified_at=c.verified_at,
                validity_note=c.validity_note,
                skills=[
                    SkillAsk(skill_id=s, label=skill_labels.get(s, s), status=ctx.status(s))  # type: ignore[arg-type]
                    for s in c.skill_ids
                ],
                role_skills=len(overlap),
                prep_course_ids=sorted(
                    {cid for cid, skills in plan_courses if skills & set(c.skill_ids)}
                ),
                openings_naming=sum(c.id in p.cert_ids for p in openings),
            )
        )
    level_order = {"foundational": 0, "associate": 1, "professional": 2}
    out.sort(key=lambda c: (-c.openings_naming, -c.role_skills, level_order[c.level], c.fee_myr))
    # With no matching certification, date the answer by when the list was last verified.
    verified = max((c.verified_at for c in out), default=None) or max(
        (c.verified_at for c in repository.certifications()), default=None
    )
    if verified is None:
        raise _unavailable()
    meta = RecommendationMeta(
        sources=[
            Source(
                name=f"{c.issuer} {c.exam_code} exam fee",
                url=c.fee_source_url,
                retrieved_at=c.verified_at,
            )
            for c in out
        ]
        or [Source(name="Adept certification list", url=PIPELINE_URL, retrieved_at=verified)],
        snapshot_date=verified,
        scenario=scenario,
        is_estimate=False,
    )
    return CertificationList(
        role_id=role_id, role_label=labels[role_id], payer=payer, certifications=out, meta=meta
    )
