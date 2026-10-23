"""Course completions: evidence ladder and HR / career-advisor review."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import accept_work_plan, work_headers

from app.contracts.pathway import Course, Progress, VerificationItem, VerificationQueue
from app.features.pathway import data, verification

ROLE = "process-automation-analyst"
HR = {"X-Demo-User": "demo-company"}
WORK = work_headers()


def _seen(client: TestClient, course_id: str) -> str | None:
    """`submitted_at` of the evidence HR sees in the queue for this course."""
    queue = VerificationQueue.model_validate(
        client.get("/api/v1/pathway/verifications", headers=HR).json()
    )
    ev = next(i.evidence for i in queue.items if i.course.id == course_id)
    return ev.submitted_at.isoformat() if ev else None


ADVISOR = {"X-Demo-User": "demo-institution"}


def _course(provider: str) -> Course:
    return Course(
        id="c",
        title="t",
        provider=provider,
        url="https://x",
        hours=1,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 20),
    )


@pytest.mark.parametrize(
    ("provider", "url", "ok"),
    [
        ("Coursera (IBM)", "https://www.coursera.org/account/accomplishments/verify/ABC123", True),
        ("Coursera (IBM)", "https://coursera.org/share/abcdef", True),
        ("Coursera (IBM)", "https://www.credly.com/badges/1234-uuid", True),
        ("Microsoft Learn", "https://learn.microsoft.com/en-us/users/jane/transcript/xyz", True),
        ("Microsoft Learn", "https://learn.microsoft.com/en-us/training/modules/x/", False),
        ("Coursera (IBM)", "https://evil.example/coursera.org/account/accomplishments/", False),
        ("UNIMAS (PROCEL)", "https://drive.google.com/file/d/cert", False),
    ],
)
def test_only_official_verification_pages_count(provider: str, url: str, ok: bool) -> None:
    assert verification.is_provider_page(url, _course(provider)) is ok


def test_link_check_needs_a_resolving_provider_page() -> None:
    course = _course("Coursera (IBM)")
    url = "https://www.coursera.org/account/accomplishments/verify/ABC"
    assert verification.check_link(url, course, lambda u: 200) == "provider_verified"
    assert verification.check_link(url, course, lambda u: 404) == "unreachable"
    assert verification.check_link(url, course, lambda u: None) == "unreachable"
    assert (
        verification.check_link("https://x.example/c", course, lambda u: 200) == "not_provider_page"
    )


def _save_and_complete(client: TestClient) -> tuple[str, str]:
    plan = client.post("/api/v1/pathway/plans", json={"role_id": ROLE}).json()["pathway"]
    course_ids = [c["id"] for s in plan["steps"] for c in s["courses"]]
    for cid in course_ids[:2]:
        client.post(
            "/api/v1/pathway/progress",
            json={"role_id": ROLE, "course_id": cid, "status": "completed"},
        )
    return course_ids[0], course_ids[1]


def _work_complete(client: TestClient) -> tuple[str, str]:
    """Aisyah completes two courses of an accepted Demo Bank programme (work learning)."""
    plan = accept_work_plan(ROLE)
    course_ids = [c.id for s in plan.steps for c in s.courses]
    for cid in course_ids[:2]:
        resp = client.post(
            "/api/v1/pathway/progress",
            json={"role_id": ROLE, "course_id": cid, "status": "completed"},
            headers=WORK,
        )
        assert resp.status_code == 200, resp.text
    return course_ids[0], course_ids[1]


def test_marking_done_is_self_reported(client: TestClient) -> None:
    first, _ = _save_and_complete(client)
    body = Progress.model_validate(
        client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    )
    assert body.evidence[first].kind == "self_reported"
    assert all(b.evidence == "self_reported" for b in body.badges)


def test_certificate_link_is_checked(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    first, _ = _save_and_complete(client)
    monkeypatch.setattr(verification, "probe", lambda url: 200)
    course = next(c for c in data.catalogue() if c.id == first)
    url = (
        "https://learn.microsoft.com/en-us/users/demo/transcript/abc"
        if "Microsoft" in course.provider
        else "https://www.credly.com/badges/demo-badge"
    )
    resp = client.post(
        "/api/v1/pathway/progress/evidence",
        json={"role_id": ROLE, "course_id": first, "url": url},
    )
    assert resp.status_code == 200, resp.text
    ev = Progress.model_validate(resp.json()).evidence[first]
    assert ev.kind == "certificate_link" and ev.link_status == "provider_verified"


def test_evidence_needs_https_and_a_planned_course(client: TestClient) -> None:
    first, _ = _save_and_complete(client)
    bad_scheme = {"role_id": ROLE, "course_id": first, "url": "http://insecure.example/cert"}
    assert client.post("/api/v1/pathway/progress/evidence", json=bad_scheme).status_code == 422
    unknown = {"role_id": ROLE, "course_id": "made-up", "url": "https://www.credly.com/badges/x"}
    resp = client.post("/api/v1/pathway/progress/evidence", json=unknown)
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "unknown_course"


def test_hr_sees_members_completions_and_confirms(client: TestClient) -> None:
    first, second = _work_complete(client)  # Aisyah is in Demo Bank
    queue = VerificationQueue.model_validate(
        client.get("/api/v1/pathway/verifications", headers=HR).json()
    )
    assert queue.pending == 2 and {i.course.id for i in queue.items} == {first, second}
    assert all(i.display_name == "Aisyah" for i in queue.items)

    decision = {
        "user_id": "aisyah",
        "role_id": ROLE,
        "course_id": first,
        "decision": "confirm",
        "note": "Attendance on HRD Corp claim",
        "submitted_at": _seen(client, first),
    }
    item = VerificationItem.model_validate(
        client.post("/api/v1/pathway/verifications", json=decision, headers=HR).json()
    )
    assert item.evidence and item.evidence.kind == "org_confirmed"
    assert item.evidence.reviewed_by == "demo-company"
    queue = VerificationQueue.model_validate(
        client.get("/api/v1/pathway/verifications", headers=HR).json()
    )
    assert queue.pending == 1


def test_rejected_completion_stops_counting(client: TestClient) -> None:
    first, _ = _work_complete(client)
    before = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}, headers=WORK).json()
    decision = {
        "user_id": "aisyah",
        "role_id": ROLE,
        "course_id": first,
        "decision": "reject",
        "note": "Certificate is for another course",
        "submitted_at": _seen(client, first),
    }
    assert (
        client.post("/api/v1/pathway/verifications", json=decision, headers=HR).status_code == 200
    )
    after = Progress.model_validate(
        client.get("/api/v1/pathway/progress", params={"role_id": ROLE}, headers=WORK).json()
    )
    assert after.percent_complete < before["percent_complete"]
    assert after.evidence[first].kind == "org_rejected"
    assert after.evidence[first].review_note == "Certificate is for another course"


def test_reviewers_only_see_their_own_members(client: TestClient) -> None:
    _work_complete(client)  # Aisyah belongs to Demo Bank, not the polytechnic
    queue = client.get("/api/v1/pathway/verifications", headers=ADVISOR).json()
    assert queue["items"] == []
    other = {
        "user_id": "aisyah",
        "role_id": ROLE,
        "course_id": "x",
        "decision": "confirm",
        "submitted_at": None,
    }
    assert (
        client.post("/api/v1/pathway/verifications", json=other, headers=ADVISOR).status_code == 403
    )


def test_review_of_changed_proof_is_refused(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _ = _work_complete(client)
    seen = _seen(client, first)  # HR opens the self-reported completion
    monkeypatch.setattr(verification, "probe", lambda url: 200)
    client.post(  # the learner then submits a certificate link
        "/api/v1/pathway/progress/evidence",
        json={"role_id": ROLE, "course_id": first, "url": "https://www.credly.com/badges/new"},
        headers=WORK,
    )
    decision = {
        "user_id": "aisyah",
        "role_id": ROLE,
        "course_id": first,
        "decision": "confirm",
        "submitted_at": seen,
    }
    resp = client.post("/api/v1/pathway/verifications", json=decision, headers=HR)
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "evidence_changed"
    ev = Progress.model_validate(
        client.get("/api/v1/pathway/progress", params={"role_id": ROLE}, headers=WORK).json()
    ).evidence[first]
    assert ev.kind == "certificate_link", "the unseen link was not confirmed"
    decision["submitted_at"] = _seen(client, first)
    resp = client.post("/api/v1/pathway/verifications", json=decision, headers=HR)
    assert resp.status_code == 200, "a review of what is stored now succeeds"


def test_probe_is_looked_up_per_call(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    first, _ = _save_and_complete(client)
    calls: list[str] = []

    def fake_probe(url: str) -> int:
        calls.append(url)
        return 200

    monkeypatch.setattr(verification, "probe", fake_probe)
    url = "https://www.credly.com/badges/offline-test"
    client.post(
        "/api/v1/pathway/progress/evidence",
        json={"role_id": ROLE, "course_id": first, "url": url},
    )
    assert calls == [url], "the patched probe is used, so tests never reach live pages"


def test_personal_learning_stays_private_until_the_member_shares_it(client: TestClient) -> None:
    first, second = _save_and_complete(client)  # personal workspace
    queue = client.get("/api/v1/pathway/verifications", headers=HR).json()
    assert queue["items"] == [], "HR never sees personal learning"

    plan = accept_work_plan(ROLE)
    work = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}, headers=WORK).json()
    assert work["workspace"] == "org-demo-bank"
    assert work["course_status"] == {}, "personal completions do not count until shared"
    assert work["completed_elsewhere"].get(first) == "personal"
    assert any(c.id == first for s in plan.steps for c in s.courses)

    shared = client.post(
        "/api/v1/pathway/progress/share",
        json={"role_id": ROLE, "course_id": first},
        headers=WORK,
    )
    assert shared.status_code == 200, shared.text
    assert shared.json()["course_status"] == {first: "completed"}
    items = client.get("/api/v1/pathway/verifications", headers=HR).json()["items"]
    assert [i["course"]["id"] for i in items] == [first], "only what was shared"
    assert items[0]["evidence"]["shared_from"] == "personal"

    # Work learning counts in the personal plan too, labelled with where it was done.
    done_at_work = next(c.id for s in plan.steps for c in s.courses if c.id not in {first, second})
    client.post(
        "/api/v1/pathway/progress",
        json={"role_id": ROLE, "course_id": done_at_work, "status": "completed"},
        headers=WORK,
    )
    mine = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    if done_at_work in {c["id"] for s in mine["pathway"]["steps"] for c in s["courses"]}:
        assert mine["completed_elsewhere"][done_at_work] == "org-demo-bank"


def test_sharing_needs_the_organisation_workspace(client: TestClient) -> None:
    first, _ = _save_and_complete(client)
    body = {"role_id": ROLE, "course_id": first}
    assert client.post("/api/v1/pathway/progress/share", json=body).status_code == 403
    outsider = {"X-Demo-User": "aisyah", "X-Workspace": "org-demo-poly"}
    assert client.get("/api/v1/pathway/progress", headers=outsider).status_code == 403


def test_learners_cannot_review(client: TestClient) -> None:
    assert client.get("/api/v1/pathway/verifications").status_code == 403


def test_retired_course_keeps_completed_credit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding P1: progress uses the saved course facts, not the live catalogue."""
    plan = client.post("/api/v1/pathway/plans", json={"role_id": ROLE}).json()["pathway"]
    rpa = next(s for s in plan["steps"] if s["skill_id"] == "rpa")
    for c in rpa["courses"]:
        client.post(
            "/api/v1/pathway/progress",
            json={"role_id": ROLE, "course_id": c["id"], "status": "completed"},
        )
    before = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    retired = {c["id"] for c in rpa["courses"]}
    live = [c for c in data.catalogue() if c.id not in retired]
    monkeypatch.setattr(data, "catalogue", lambda: live)
    monkeypatch.setattr(data, "course_index", lambda: {c.id: c for c in live})
    after = client.get("/api/v1/pathway/progress", params={"role_id": ROLE}).json()
    level = lambda body: next(s for s in body["skills"] if s["skill_id"] == "rpa")["current_level"]  # noqa: E731
    assert level(after) == level(before) >= 3
    assert after["gap_closed"] == before["gap_closed"]
