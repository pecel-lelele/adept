"""Job pipeline: role rules, skill/cert extraction, location filters and connector parsing."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from pipelines.jobs import classify, sources
from pipelines.jobs.boards import Board
from pipelines.jobs.certifications import CERTS
from pipelines.jobs.classify import RoleReq, assign_role, cert_mentions, role_from_title, seniority
from pipelines.jobs.run import requirements

# Hand-labelled titles from real Malaysian ads (Oct 2026) -> the Adept role a careers adviser
# would file them under (None = no Adept role fits). Title rules must get these right.
LABELLED: list[tuple[str, str | None]] = [
    ("Securities & Derivatives Analyst", None),
    ("Securities Services Officer", None),
    ("Securitization Operations", None),
    ("Senior Data Analyst", "data-analyst"),
    ("Business Intelligence Analyst", "data-analyst"),
    ("Data Engineer (Kuala Lumpur)", "data-engineer"),
    ("Machine Learning Engineer", "machine-learning-engineer"),
    ("Data Scientist - Risk", "machine-learning-engineer"),
    ("RPA Developer (UiPath)", "process-automation-analyst"),
    ("Intelligent Automation Analyst", "process-automation-analyst"),
    ("AML Compliance Officer", "compliance-analytics-officer"),
    ("KYC Analyst", "compliance-analytics-officer"),
    ("SOC Analyst L2", "cybersecurity-analyst"),
    ("Information Security Engineer", "cybersecurity-analyst"),
    ("Cloud Engineer (AWS)", "cloud-solutions-architect"),
    ("Site Reliability Engineer", "cloud-solutions-architect"),
    ("Product Manager, Payments", "ai-product-manager"),
    ("Senior UX Designer", "ux-designer"),
    ("Product Designer", "ux-designer"),
    ("Performance Marketing Manager", "digital-marketing-specialist"),
    ("Business Analyst - Core Banking", "business-analyst"),
    ("Process Engineer, Wafer Fab", "semiconductor-process-engineer"),
    ("Failure Analysis Engineer", "semiconductor-process-engineer"),
    ("Manufacturing Engineer", "smart-manufacturing-engineer"),
    ("Supply Chain Planner", "supply-chain-analyst"),
    ("ESG Reporting Analyst", "esg-sustainability-analyst"),
    ("Customer Success Manager", "customer-success-specialist"),
    ("Shariah Compliance Officer", "islamic-finance-analyst"),
    ("HR Analyst (People Analytics)", "people-analytics-specialist"),
    ("Responsible AI Lead", "responsible-ai-officer"),
    ("Hub Supervisor", "logistics-supervisor"),
    ("Manufacturing Shift Trainer", "smart-manufacturing-engineer"),
    ("Senior Backend Engineer (Go)", None),
    ("Tax Manager", None),
]


@pytest.mark.parametrize(("title", "expected"), LABELLED)
def test_title_rules_on_labelled_titles(title: str, expected: str | None) -> None:
    assert role_from_title(title) == expected


def test_title_rules_precision_and_every_role_exists() -> None:
    hits = sum(role_from_title(t) == e for t, e in LABELLED)
    assert hits / len(LABELLED) >= 0.95
    reqs = requirements()
    assert {rid for rid, _ in classify.ROLE_TITLES} <= set(reqs)


def test_roles_come_from_titles_only() -> None:
    reqs = {"data-analyst": [RoleReq("sql", 1.0)]}
    assert assign_role("Senior Data Analyst", reqs) == ("data-analyst", "title")
    assert assign_role("Engineer II", reqs) == (None, "")  # skills alone never assign a role
    assert assign_role("Machine Learning Engineer", reqs) == (None, "")  # role not in catalogue
    assert role_from_title("Corporate Counsel, Compliance") is None
    assert role_from_title("Driver / Rider - Johor") is None


def test_cert_mentions_by_code_and_name() -> None:
    text = "Nice to have: PL-300 or AWS Certified Cloud Practitioner; AZ900 a plus."
    assert set(cert_mentions(text)) == {"ms-pl-300", "aws-clf-c02", "ms-az-900"}
    assert cert_mentions("We use Power BI daily") == []
    assert {c for c, _ in classify.CERT_PATTERNS} == {c.id for c in CERTS}


def test_certifications_are_dated_priced_and_use_catalogue_skills() -> None:
    skills = {r.skill_id for reqs in requirements().values() for r in reqs}
    for c in CERTS:
        assert c.fee_amount > 0 and c.fee_source_url.startswith("https://")
        assert c.url.startswith("https://") and c.verified_at <= date.today()
        assert set(c.skill_ids) & skills, c.id


@pytest.mark.parametrize(
    ("title", "hint", "expected"),
    [
        ("Internship in Quality Management", "", "intern"),
        ("Graduate Trainee - Finance", "", "intern"),
        ("Junior Data Analyst", "", "entry"),
        ("Senior Data Engineer", "", "senior"),
        ("Head of Product", "", "lead"),
        ("Data Analyst", "Associate", "mid"),
        ("Data Analyst", "Mid-Senior level", "senior"),
        ("Data Analyst", "", "unknown"),
    ],
)
def test_seniority(title: str, hint: str, expected: str) -> None:
    assert seniority(title, hint) == expected


@pytest.mark.parametrize(
    ("location", "work_mode", "scope", "expected"),
    [
        ("Kuala Lumpur, Malaysia", "onsite", "", "in_malaysia"),
        ("Abu Dhabi, UAE; Kuala Lumpur, Malaysia", "onsite", "", "in_malaysia"),
        ("Malaysia-Remote Location", "remote", "Malaysia", "in_malaysia"),
        ("Remote", "remote", "Malaysia", "remote_explicit_my"),
        ("Remote", "remote", "APAC", "remote_explicit_my"),
        ("Anywhere", "remote", "Southeast Asia", "remote_explicit_my"),
        ("", "remote", "Asia", "remote_explicit_my"),
        ("Remote", "remote", "Worldwide", "remote_assumed_worldwide"),
        ("Remote", "remote", "", "not_malaysia"),
        ("LATAM - Remote", "remote", "Malaysia", "not_malaysia"),
        ("Singapore-Yishun", "remote", "Malaysia", "not_malaysia"),
        ("APAC - Remote; Hong Kong SAR", "remote", "Malaysia", "not_malaysia"),
        ("Singapore", "onsite", "", "not_malaysia"),
        ("Remote", "hybrid", "Worldwide", "not_malaysia"),
    ],
)
def test_malaysia_relevance(location: str, work_mode: str, scope: str, expected: str) -> None:
    assert sources.malaysia_relevance(location, work_mode, scope) == expected


def test_location_filters() -> None:
    assert sources.in_malaysia("Bayan Lepas, Penang")
    assert not sources.in_malaysia("Singapore", "Fab 10A")
    assert sources.remote_scope("APAC") == "APAC"
    assert sources.remote_scope("Anywhere in the World") == "Worldwide"
    assert sources.remote_scope("USA only") == ""
    assert sources.html_to_text("&lt;p&gt;SQL &amp;amp; Python&lt;/p&gt;") == "SQL & Python"


class FakeFetcher:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def get_json(self, url: str, **_: Any) -> Any:
        return self.payload


def test_greenhouse_keeps_only_malaysian_openings() -> None:
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Data Analyst",
                "absolute_url": "https://x/1",
                "location": {"name": "Kuala Lumpur"},
                "content": "&lt;p&gt;SQL&lt;/p&gt;",
                "first_published": "2026-10-20T01:00:00Z",
            },
            {
                "id": 2,
                "title": "Data Analyst",
                "absolute_url": "https://x/2",
                "location": {"name": "Bangkok"},
                "content": "",
            },
        ]
    }
    found = list(sources.greenhouse(FakeFetcher(payload), Board("greenhouse", "acme", "Acme")))  # type: ignore[arg-type]
    assert [p.source_id for p in found] == ["1"]
    assert found[0].posted_at == date(2026, 10, 20) and "SQL" in found[0].text


def test_lever_reads_location_and_mode() -> None:
    payload = [
        {
            "id": "a",
            "text": "RPA Developer",
            "hostedUrl": "https://x/a",
            "categories": {"location": "Kuala Lumpur", "commitment": "Full-time"},
            "workplaceType": "hybrid",
            "descriptionPlain": "UiPath",
            "lists": [],
            "createdAt": 1792800000000,
        },
        {
            "id": "b",
            "text": "Driver",
            "hostedUrl": "https://x/b",
            "categories": {"location": "Jakarta"},
        },
    ]
    found = list(sources.lever(FakeFetcher(payload), Board("lever", "acme", "Acme")))  # type: ignore[arg-type]
    assert (
        len(found) == 1
        and found[0].work_mode == "hybrid"
        and found[0].employment_type == "Full-time"
    )


def test_missing_key_skips_keyed_boards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOOBLE_API_KEY", raising=False)
    with pytest.raises(sources.MissingKey):
        list(sources.jooble(FakeFetcher({}), Board("jooble", "jooble-my", "")))  # type: ignore[arg-type]


def test_employer_boilerplate_skills_are_dropped() -> None:
    from pipelines.jobs.run import boilerplate_skills

    ads = [
        {"ai-ethics", "sql"},
        {"ai-ethics", "python"},
        {"ai-ethics"},
        {"ai-ethics", "excel"},
        {"ai-ethics"},
    ]
    assert boilerplate_skills({"jibe:amd": ads}) == {"jibe:amd": {"ai-ethics"}}
    assert boilerplate_skills({"small": ads[:3]}) == {}  # too few ads to tell
