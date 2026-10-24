"""Paid certification exams that follow catalogue courses, checked by hand on the issuer's site.

A course teaches; a certification exam proves it to an employer and has its own fee. Each row
quotes the fee for a candidate in Malaysia (Microsoft prices exams by country), the page it was
read from and the date. Ringgit amounts are converted at Bank Negara Malaysia's selling rate.
Validity is stated only where the issuer's page says it. Fees change: confirm at checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

VERIFIED = date(2026, 10, 23)
MS_PRICING = "https://learn.microsoft.com/en-us/credentials/exam-pricing.json"


@dataclass(frozen=True)
class Cert:
    id: str
    name: str
    issuer: str
    exam_code: str
    url: str
    fee_amount: float
    fee_currency: str
    fee_source_url: str
    level: str  # foundational | associate | professional
    skill_ids: tuple[str, ...]
    fee_detail: str = ""
    validity_note: str = ""
    verified_at: date = VERIFIED


def _ms(code: str, slug: str, name: str, fee: float, level: str, skills: tuple[str, ...]) -> Cert:
    return Cert(
        id=f"ms-{code.lower()}",
        name=name,
        issuer="Microsoft",
        exam_code=code,
        url=f"https://learn.microsoft.com/en-us/credentials/certifications/{slug}/",
        fee_amount=fee,
        fee_currency="USD",
        fee_source_url=MS_PRICING,
        level=level,
        skill_ids=skills,
        fee_detail="Microsoft's listed exam price for Malaysia; taxes may apply.",
    )


CERTS: tuple[Cert, ...] = (
    _ms(
        "PL-900",
        "power-platform-fundamentals",
        "Microsoft Certified: Power Platform Fundamentals",
        50,
        "foundational",
        ("low-code-ai", "rpa", "process-mapping"),
    ),
    _ms(
        "PL-300",
        "data-analyst-associate",
        "Microsoft Certified: Power BI Data Analyst Associate",
        83,
        "associate",
        ("data-visualisation", "excel", "statistics", "report-generation"),
    ),
    _ms(
        "DP-900",
        "azure-data-fundamentals",
        "Microsoft Certified: Azure Data Fundamentals",
        50,
        "foundational",
        ("sql", "data-pipelines"),
    ),
    _ms(
        "DP-700",
        "fabric-data-engineer-associate",
        "Microsoft Certified: Fabric Data Engineer Associate",
        83,
        "associate",
        ("data-pipelines", "sql-advanced", "sql"),
    ),
    _ms(
        "AZ-900",
        "azure-fundamentals",
        "Microsoft Certified: Azure Fundamentals",
        50,
        "foundational",
        ("cloud-computing",),
    ),
    _ms(
        "AZ-104",
        "azure-administrator",
        "Microsoft Certified: Azure Administrator Associate",
        83,
        "associate",
        ("cloud-computing", "enterprise-architecture"),
    ),
    _ms(
        "AI-901",
        "azure-ai-fundamentals",
        "Microsoft Certified: Azure AI Fundamentals",
        50,
        "foundational",
        ("ai-literacy", "cloud-ai-services", "prompt-engineering"),
    ),
    _ms(
        "SC-900",
        "security-compliance-and-identity-fundamentals",
        "Microsoft Certified: Security, Compliance, and Identity Fundamentals",
        50,
        "foundational",
        ("cybersecurity-governance", "risk-compliance", "data-privacy"),
    ),
    _ms(
        "SC-200",
        "security-operations-analyst",
        "Microsoft Certified: Security Operations Analyst Associate",
        83,
        "associate",
        ("cybersecurity-operations", "security-ai"),
    ),
    Cert(
        id="aws-clf-c02",
        name="AWS Certified Cloud Practitioner",
        issuer="Amazon Web Services",
        exam_code="CLF-C02",
        url="https://aws.amazon.com/certification/certified-cloud-practitioner/",
        fee_amount=100,
        fee_currency="USD",
        fee_source_url="https://aws.amazon.com/certification/certified-cloud-practitioner/",
        level="foundational",
        skill_ids=("cloud-computing",),
        fee_detail="AWS lists 100 USD; additional costs, including foreign exchange, may apply.",
        validity_note="Valid for 3 years.",
    ),
    Cert(
        id="aws-aif-c01",
        name="AWS Certified AI Practitioner",
        issuer="Amazon Web Services",
        exam_code="AIF-C01",
        url="https://aws.amazon.com/certification/certified-ai-practitioner/",
        fee_amount=100,
        fee_currency="USD",
        fee_source_url="https://aws.amazon.com/certification/certified-ai-practitioner/",
        level="foundational",
        skill_ids=("ai-literacy", "cloud-ai-services", "prompt-engineering", "ai-ethics"),
        fee_detail="AWS lists 100 USD; additional costs, including foreign exchange, may apply.",
        validity_note="Valid for 3 years.",
    ),
    Cert(
        id="gcp-cdl",
        name="Google Cloud Certified: Cloud Digital Leader",
        issuer="Google Cloud",
        exam_code="Cloud Digital Leader",
        url="https://cloud.google.com/learn/certification/cloud-digital-leader",
        fee_amount=99,
        fee_currency="USD",
        fee_source_url="https://cloud.google.com/learn/certification/cloud-digital-leader",
        level="foundational",
        skill_ids=("cloud-computing", "cloud-ai-services"),
        fee_detail="Registration fee 99 USD, plus tax where applicable.",
        validity_note="Valid for 3 years.",
    ),
    Cert(
        id="iiba-ecba",
        name="IIBA Entry Certificate in Business Analysis (ECBA)",
        issuer="International Institute of Business Analysis",
        exam_code="ECBA",
        url="https://www.iiba.org/business-analysis-certifications/ecba/",
        fee_amount=395,
        fee_currency="USD",
        fee_source_url="https://www.iiba.org/business-analysis-certifications/ecba/",
        level="foundational",
        skill_ids=("business-analysis", "process-mapping", "stakeholder-management"),
        fee_detail=(
            "IIBA lists '$395 or less' for a bundle with membership, the exam, a practice exam "
            "and the learning journey; regional and student prices can be lower."
        ),
    ),
    Cert(
        id="iapp-aigp",
        name="IAPP Artificial Intelligence Governance Professional (AIGP)",
        issuer="International Association of Privacy Professionals",
        exam_code="AIGP",
        url="https://iapp.org/certify/aigp/",
        fee_amount=799,
        fee_currency="USD",
        fee_source_url="https://store.iapp.org/aigp-exam/",
        level="professional",
        skill_ids=("ai-ethics", "ai-safety", "bias-auditing", "data-governance-ai", "data-privacy"),
        fee_detail="799 USD for non-members; 649 USD for IAPP members.",
    ),
)
