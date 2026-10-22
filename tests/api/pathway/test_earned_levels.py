"""H08: completed learning raises matching levels only with accepted evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.contracts.pathway import CompletionEvidence, Course
from app.features.matching import repository as matching_repository
from app.features.pathway import service as pathway_service
from app.features.pathway.verification import effective_statuses

NOW = datetime(2026, 10, 22, tzinfo=UTC)


def _course(cid: str, skills: list[str], level: int) -> Course:
    return Course(
        id=cid,
        title=cid,
        provider="p",
        url="https://example.test/c",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 1),
        skill_ids=skills,
        level=level,
    )


def _evidence(cid: str, kind: str, link_status: str = "not_submitted") -> CompletionEvidence:
    return CompletionEvidence(
        role_id="r",
        course_id=cid,
        kind=kind,  # type: ignore[arg-type]
        link_status=link_status,  # type: ignore[arg-type]
        submitted_at=NOW,
    )


COURSES = {
    "self": _course("self", ["sql"], 3),
    "cert-ok": _course("cert-ok", ["python"], 3),
    "cert-bad": _course("cert-bad", ["excel"], 3),
    "confirmed": _course("confirmed", ["sql", "viz"], 4),
    "rejected": _course("rejected", ["ml"], 4),
    "open": _course("open", ["stats"], 3),
}


def test_only_reviewed_or_provider_checked_completions_count() -> None:
    evidence = {
        "cert-ok": _evidence("cert-ok", "certificate_link", "provider_verified"),
        "cert-bad": _evidence("cert-bad", "certificate_link", "unreachable"),
        "confirmed": _evidence("confirmed", "org_confirmed"),
        "rejected": _evidence("rejected", "org_rejected"),
    }
    raw = {cid: "completed" for cid in COURSES if cid != "open"} | {"open": "in_progress"}
    statuses = effective_statuses(raw, evidence)  # type: ignore[arg-type]
    earned = pathway_service.earned_levels(COURSES, statuses, evidence)
    assert earned == {"python": 3, "sql": 4, "viz": 4}
    # self-ticked (sql via "self"), an unreachable link, a rejection and an unfinished course
    # change nothing; the strongest level wins per skill.
    assert "excel" not in earned and "ml" not in earned and "stats" not in earned


def test_matching_uses_the_higher_of_intake_and_evidenced_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = matching_repository.load_profile("aisyah").skills
    skill = next(iter(before))
    monkeypatch.setattr(
        pathway_service, "evidenced_levels", lambda user_id: {skill: 5, "new-skill": 2}
    )
    after = matching_repository.load_profile("aisyah").skills
    assert after[skill] == 5.0
    assert after["new-skill"] == 2.0
    assert {k: v for k, v in after.items() if k not in (skill, "new-skill")} == {
        k: v for k, v in before.items() if k != skill
    }
    monkeypatch.setattr(pathway_service, "evidenced_levels", lambda user_id: {skill: 1})
    assert matching_repository.load_profile("aisyah").skills[skill] == before[skill]
