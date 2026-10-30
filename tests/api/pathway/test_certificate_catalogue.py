"""Certificate-required plans need dated provider evidence independent of learning price."""

from datetime import date

import pytest

from app.contracts.common import Source
from app.contracts.pathway import Course
from app.contracts.programmes import ProgrammeBriefIn
from app.core import seed
from app.features.org import programmes
from app.features.pathway import data, engine, service


def _brief(required: bool) -> ProgrammeBriefIn:
    # Only catalogue restrictions are relevant here; no programme is saved or sent.
    return ProgrammeBriefIn.model_construct(
        certificate_required=required,
        hrd_claimable_only=False,
        formats=["self_paced", "live_online", "in_person", "hybrid"],
    )


def test_verified_certificates_resolve_to_courses_and_provider_sources() -> None:
    evidence = data.certificate_evidence()
    courses = data.course_index()
    assert evidence and set(evidence) <= set(courses)
    for cid, fact in evidence.items():
        course = courses[cid]
        assert course.certificate_status == "included"
        assert course.certificate_source == fact.source
        assert fact.source.url == course.url and fact.source.retrieved_at == date(2026, 10, 31)
    allowed = {c.id for c in programmes._catalogue(_brief(True))}
    assert allowed == set(evidence)
    pepper = {cid for cid in courses if cid.startswith("pepperlabs-")}
    assert len(pepper) == 3 and not allowed & pepper
    assert pepper <= {c.id for c in programmes._catalogue(_brief(False))}
    assert all(courses[cid].certificate_status == "unknown" for cid in pepper)
    assert all(courses[cid].price_status == "listed" for cid in pepper)
    # Verified certificate dates do not pretend fees/hours were rechecked today.
    assert all(courses[cid].verified_at == date(2026, 10, 30) for cid in evidence)
    assert {row["id"] for row in seed.rows("courses", "courses")} >= set(evidence)


def test_unknown_certificates_never_leak_into_selected_courses_or_alternatives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Source(
        name="Synthetic certificate evidence",
        url="https://example.test/certificate",
        retrieved_at="2026-10-31",
    )
    base = Course(
        id="synthetic-verified",
        title="Synthetic verified course",
        provider="Synthetic provider",
        url="https://example.test/course",
        hours=2,
        cost_myr=10,
        hrd_claimable=False,
        verified_at="2026-10-30",
        skill_ids=["sql"],
        level=3,
        certificate_status="included",
        certificate_source=source,
        source=source,
    )
    rows = [
        base,
        base.model_copy(update={"id": "synthetic-alternative", "cost_myr": 11}),
        base.model_copy(
            update={
                "id": "synthetic-unknown-free",
                "cost_myr": 0,
                "certificate_status": "unknown",
                "certificate_source": None,
            }
        ),
        base.model_copy(
            update={
                "id": "synthetic-unknown-paid",
                "cost_myr": 1,
                "certificate_status": "unknown",
                "certificate_source": None,
            }
        ),
        base.model_copy(
            update={"id": "synthetic-no-evidence", "cost_myr": 0, "certificate_source": None}
        ),
        base.model_copy(
            update={
                "id": "synthetic-unknown-cert-price",
                "price_status": "certificate_price_unknown",
            }
        ),
    ]
    monkeypatch.setattr(data, "catalogue", lambda: rows)
    filtered = programmes._catalogue(_brief(True))
    assert {c.id for c in filtered} == {"synthetic-verified", "synthetic-alternative"}
    plan = service.build_pathway(
        engine.Learner({}, 5, 100, False), "data-analyst", "moderate", catalogue=filtered
    )
    selected = [c for step in plan.steps for c in step.courses]
    alternatives = [c for step in plan.steps for c in step.alternatives]
    assert selected and alternatives  # non-vacuous selected/alternative regression
    assert all(
        c.certificate_status == "included" and c.certificate_source for c in selected + alternatives
    )
    assert source in plan.meta.sources
