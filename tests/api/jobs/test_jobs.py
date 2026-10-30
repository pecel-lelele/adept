"""Live openings API: fit maths, learner/plan statuses, certifications and the HTTP contract."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.contracts.jobs import CertificationList, JobBoardPage, OpeningsSummary, RoleOpenings
from app.features.jobs import fit, repository, service
from app.features.jobs.repository import CertRow, Posting

TODAY = date.today()


def test_csv_read_excludes_stale_openings_even_when_refresh_stops(monkeypatch):
    base = {
        "id": "public-job",
        "source": "greenhouse",
        "board": "demo",
        "source_name": "Demo",
        "employer": "Fictional employer",
        "title": "Data Analyst",
        "location": "Kuala Lumpur, Malaysia",
        "url": "https://example.test/job",
        "api_url": "https://example.test/feed",
        "first_seen": TODAY.isoformat(),
        "active": "true",
    }
    rows = [
        dict(base, id=str(days), last_seen=(TODAY - timedelta(days=days)).isoformat())
        for days in [0, 14, 15]
    ]
    rows += [
        dict(base, id="worldwide", location="Worldwide", last_seen=TODAY.isoformat()),
        dict(base, id="singapore", location="Singapore", last_seen=TODAY.isoformat()),
    ]
    monkeypatch.setattr(repository.refdata, "rows", lambda *args, **kwargs: rows)
    assert {p.id for p in repository.openings()} == {"0", "14"}


def _posting(pid: str, role: str, skills: tuple[str, ...], **kw: object) -> Posting:
    base: dict[str, object] = {
        "id": pid,
        "source": "greenhouse",
        "board": "acme",
        "source_name": "Greenhouse job board",
        "employer": "Acme",
        "title": "Data Analyst",
        "location": "Kuala Lumpur",
        "work_mode": "onsite",
        "remote_scope": "",
        "employment_type": "",
        "seniority": "mid",
        "url": f"https://boards.greenhouse.io/acme/jobs/{pid}",
        "api_url": "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        "posted_at": TODAY - timedelta(days=3),
        "first_seen": TODAY,
        "last_seen": TODAY,
        "role_id": role,
        "role_method": "title",
        "skill_ids": skills,
        "cert_ids": (),
    }
    base.update(kw)
    return Posting(**base)  # type: ignore[arg-type]


POSTINGS = [
    _posting("1", "data-analyst", ("sql", "excel", "data-visualisation"), cert_ids=("ms-pl-300",)),
    _posting(
        "2",
        "data-analyst",
        ("python", "statistics", "sql"),
        employer="Beta",
        work_mode="remote",
        remote_scope="APAC",
    ),
    _posting("3", "data-analyst", ("sql",), employer="Beta"),
    _posting("4", "data-engineer", ("python", "data-pipelines")),
]
CERT = CertRow(
    id="ms-pl-300",
    name="Microsoft Certified: Power BI Data Analyst Associate",
    issuer="Microsoft",
    exam_code="PL-300",
    url="https://learn.microsoft.com/en-us/credentials/certifications/data-analyst-associate/",
    level="associate",
    fee_amount=83,
    fee_currency="USD",
    fee_myr=339.3,
    fee_note="Listed as USD 83.",
    fee_source_url="https://learn.microsoft.com/en-us/credentials/exam-pricing.json",
    verified_at=date(2026, 10, 23),
    validity_note="",
    skill_ids=("data-visualisation", "excel", "statistics"),
)
UNRELATED = CertRow(**{**CERT.__dict__, "id": "x", "skill_ids": ("patient-care",)})


@pytest.fixture
def feed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "openings", lambda: list(POSTINGS))
    monkeypatch.setattr(repository, "certifications", lambda: [CERT, UNRELATED])


def test_status_uses_role_level_then_plan() -> None:
    required = {"sql": 3}
    assert fit.status("sql", {"sql": 3}, {}, required) == "have"
    assert fit.status("sql", {"sql": 2}, {"sql": 3}, required) == "in_plan"
    assert fit.status("sql", {"sql": 2}, {"sql": 2}, required) == "missing"
    assert fit.status("python", {"python": 2}, {}, required) == "have"  # default level 2
    assert fit.status("sql", None, {}, required) == "not_rated"


def test_shares_need_two_skills() -> None:
    assert fit.shares(["have"]) == (None, None)
    assert fit.shares(["have", "in_plan", "missing"]) == (0.333, 0.667)
    assert fit.within_reach(0.6) and not fit.within_reach(0.59) and not fit.within_reach(None)


def test_demand_counts_each_ad_once() -> None:
    assert fit.demand([("sql", "sql", "excel"), ("sql",)]) == [("sql", 2), ("excel", 1)]


def test_summary_counts_roles(feed: None) -> None:
    s = service.summary()
    counts = {r.role_id: r.open_count for r in s.roles}
    assert counts == {"data-analyst": 3, "data-engineer": 1}
    assert s.total_open == 4 and s.employer_count == 2
    assert s.meta.sources[0].url.startswith("https://boards-api.greenhouse.io")


def test_role_openings_rates_against_learner_and_plan(client: TestClient, feed: None) -> None:
    resp = client.get("/api/v1/jobs/roles/data-analyst")
    assert resp.status_code == 200, resp.text
    body = RoleOpenings.model_validate(resp.json())
    assert body.open_count == 3 and body.employer_count == 2 and body.remote_count == 1
    assert body.employers[0] == "Beta"  # two openings
    assert body.rated == 2  # the single-skill ad is not rated
    assert body.ready_after_plan >= body.ready_now
    assert body.skill_demand[0].skill_id == "sql" and body.skill_demand[0].openings == 3
    for o in body.openings:
        assert o.url.startswith("https://")
        if o.match_now is not None and o.match_after_plan is not None:
            assert o.match_after_plan >= o.match_now
    # Rated openings come before unrated ones.
    rated_flags = [o.match_now is not None for o in body.openings]
    assert rated_flags == sorted(rated_flags, reverse=True)
    assert body.meta.is_estimate


def test_unknown_role_is_404(client: TestClient, feed: None) -> None:
    assert client.get("/api/v1/jobs/roles/not-a-role").status_code == 404


def test_board_filters(client: TestClient, feed: None) -> None:
    body = JobBoardPage.model_validate(
        client.get("/api/v1/jobs/board", params={"work_mode": "remote"}).json()
    )
    assert body.total == 1 and body.openings[0].employer == "Beta"
    body = JobBoardPage.model_validate(
        client.get("/api/v1/jobs/board", params={"q": "acme"}).json()
    )
    assert {o.employer for o in body.openings} == {"Acme"}


def test_certifications_for_role(client: TestClient, feed: None) -> None:
    resp = client.get("/api/v1/jobs/certifications", params={"role_id": "data-analyst"})
    body = CertificationList.model_validate(resp.json())
    assert [c.id for c in body.certifications] == ["ms-pl-300"]  # unrelated exam left out
    cert = body.certifications[0]
    assert cert.openings_naming == 1 and cert.role_skills >= 1
    assert body.payer == "learner"
    assert {s.status for s in cert.skills} <= {"have", "in_plan", "missing"}


def test_employer_view_does_not_show_learner_skills(client: TestClient, feed: None) -> None:
    body = CertificationList.model_validate(
        client.get(
            "/api/v1/jobs/certifications", params={"role_id": "data-analyst", "payer": "employer"}
        ).json()
    )
    assert body.payer == "employer"
    assert {s.status for c in body.certifications for s in c.skills} == {"not_rated"}


def test_seed_feed_is_well_formed(client: TestClient) -> None:
    """Whatever the committed snapshot holds, the API serves it within the contract."""
    s = OpeningsSummary.model_validate(client.get("/api/v1/jobs/summary").json())
    assert s.total_open == sum(r.open_count for r in s.roles)
    for p in repository.openings():
        assert p.url.startswith("https://") and p.title


def test_empty_result_is_dated_by_the_feed_not_the_request(monkeypatch) -> None:
    """No fabricated freshness: an empty answer carries the last real fetch date."""
    from datetime import date

    from app.core.errors import AppError
    from app.features.jobs import service as jobs_service

    monkeypatch.setattr(repository, "fetch_log", lambda: {"fetched_on": "2026-10-23"})
    meta = jobs_service._meta([], "moderate")
    assert meta.snapshot_date == date(2026, 10, 23)
    assert {s.retrieved_at for s in meta.sources} == {date(2026, 10, 23)}

    monkeypatch.setattr(repository, "fetch_log", lambda: {})
    monkeypatch.setattr(repository, "observation_date", lambda: None)
    with pytest.raises(AppError) as error:
        jobs_service._meta([], "moderate")
    assert error.value.status_code == 503
