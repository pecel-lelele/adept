"""Course catalogue sources (F5). Used by the offline pipeline (`pipelines.pathway.run`) and by
live sync (`app.features.pathway.sync`), so both always build the same rows.

The pathway may only recommend catalogue courses. Three kinds of rows:

1. **Microsoft Learn Catalog API** (`CURATED`): free modules and learning paths. Title, URL
   and duration come from the API at fetch time.
2. **Coursera** (`COURSERA`): courses whose page says "Enroll for free". Hours are the sum of
   the module hours on the course page, checked by hand on `verified_at`; live sync checks
   through Coursera's public catalog API that each course still exists.
3. **HRD Corp-claimable provider courses** (`MANUAL`): paid courses whose own page or
   brochure states the fee and HRD Corp claimability, quoted in `hrd_note`.

`level` is the skill level (1-5) Adept estimates a learner reaches after the course: an Adept
judgment, shown to users as an estimate.
"""

from __future__ import annotations

import csv
import json
import math
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

MSLEARN_API = (
    "https://learn.microsoft.com/api/learn/catalog?locale=en-us&type=modules,learningPaths"
)
MSLEARN_SOURCE = "Microsoft Learn Catalog API"
MSLEARN_SOURCE_URL = "https://learn.microsoft.com/en-us/training/support/catalog-api"
COURSERA_API = "https://api.coursera.org/api/courses.v1?q=slug&slug={slug}&fields=workload"
CHECKED = date(2026, 10, 20)
CHECKED_2 = date(2026, 10, 23)  # catalogue enrichment pass
CHECKED_3 = date(2026, 10, 30)  # Bahasa Melayu course pass


@dataclass(frozen=True)
class Curated:
    id: str
    uid: str
    skill_ids: tuple[str, ...]
    level: int


CURATED: tuple[Curated, ...] = (
    Curated("mslearn-genai-at-work", "learn-m365.what-generative-ai", ("ai-literacy",), 1),
    Curated("mslearn-ai-literacy", "learn.mec.introduction-ai-literacy", ("ai-literacy",), 2),
    Curated(
        "mslearn-explore-responsible-ai",
        "learn.philanthropies.explore-responsible-ai",
        ("ai-literacy",),
        2,
    ),
    Curated(
        "mslearn-responsible-ai",
        "learn.wwl.embrace-responsible-ai-principles-practices",
        ("ai-literacy",),
        3,
    ),
    Curated(
        "mslearn-effective-prompts",
        "learn.wwl.write-effective-prompts-do-more-prompting",
        ("prompt-engineering",),
        2,
    ),
    Curated(
        "mslearn-prompts-genai-tools",
        "learn.philanthropies.create-prompts-for-generative-ai-training-tools",
        ("prompt-engineering",),
        2,
    ),
    Curated("mslearn-python-1", "learn.wwl.get-started-with-python-fundamentals", ("python",), 2),
    Curated("mslearn-python-data", "learn.wwl.work-with-data-python", ("python",), 2),
    Curated("mslearn-python-2", "learn.wwl.get-started-with-python-programs", ("python",), 3),
    Curated("mslearn-relational-data", "learn.wwl.explore-relational-data-offerings", ("sql",), 1),
    Curated("mslearn-tsql", "learn.wwl.get-started-querying-with-transact-sql", ("sql",), 3),
    Curated(
        "mslearn-data-analytics", "learn.wwl.get-started-data-analytics", ("data-visualisation",), 1
    ),
    Curated(
        "mslearn-dataviz-fundamentals",
        "learn.wwl.explore-fundamentals-of-data-visualization",
        ("data-visualisation",),
        2,
    ),
    Curated(
        "mslearn-power-bi", "learn.wwl.prepare-visualize-data-power-bi", ("data-visualisation",), 3
    ),
    Curated(
        "mslearn-power-automate",
        "learn-bizapps.automate-process-using-flow",
        ("process-mapping",),
        2,
    ),
    Curated(
        "mslearn-process-mining",
        "learn-bizapps.introduction-process-advisor",
        ("process-mapping",),
        3,
    ),
    Curated("mslearn-pad-start", "learn-bizapps.pad-get-started", ("rpa",), 2),
    Curated("mslearn-pad-excel", "learn-bizapps.pad-excel-automation", ("rpa",), 2),
    Curated("mslearn-pad-work", "learn-bizapps.pad-work", ("rpa",), 3),
    Curated(
        "mslearn-security-compliance",
        "learn.wwl.describe-concepts-of-security-compliance-identity",
        ("risk-compliance",),
        2,
    ),
    Curated("mslearn-ux-foundations", "learn.startup.ux-design", ("ux-design", "ux-research"), 2),
    Curated(
        "mslearn-cloud-foundations",
        "learn.wwl.microsoft-azure-fundamentals-describe-cloud-concepts",
        ("cloud-computing",),
        2,
    ),
    Curated(
        "mslearn-ml-experiments",
        "learn.wwl.experiment-azure-machine-learning",
        ("machine-learning",),
        2,
    ),
    Curated(
        "mslearn-mlops-foundations",
        "learn.wwl.introduction-development-operations-principles-for-machine-learn",
        ("mlops",),
        2,
    ),
    Curated(
        "mslearn-model-tracking",
        "learn.wwl.train-track-model-fabric",
        ("model-monitoring", "mlops"),
        2,
    ),
    Curated(
        "mslearn-ml-deployment",
        "learn.wwl.continuous-deployment-for-machine-learning",
        ("mlops",),
        3,
    ),
    Curated(
        "mslearn-security-operations",
        "learn.wwl.design-solutions-security-operations",
        ("cybersecurity-operations", "cybersecurity-governance"),
        2,
    ),
    Curated(
        "mslearn-sentinel-siem",
        "learn.wwl.configure-siem-security-operations-using-microsoft-sentinel-labs",
        ("cybersecurity-operations",),
        3,
    ),
    Curated(
        "mslearn-sustainable-datacenters",
        "learn.philanthropies.describe-sustainability-practices-datacenters",
        ("energy-efficiency",),
        1,
    ),
    Curated(
        "mslearn-sustainability-manager",
        "learn-bizapps.work-cloud-sustainability",
        ("esg-reporting", "carbon-accounting"),
        2,
    ),
    Curated(
        "mslearn-emissions-ingestion",
        "learn-bizapps.sustainability-data-ingestion",
        ("carbon-accounting", "esg-reporting"),
        2,
    ),
    Curated(
        "mslearn-carbon-goals",
        "learn-bizapps.sustainability-goals-scorecard",
        ("carbon-accounting",),
        2,
    ),
    Curated(
        "mslearn-supply-chain-foundations",
        "learn.wwl.describe-core-capabilities-supply-chain-management",
        ("supply-chain-strategy", "logistics-planning"),
        2,
    ),
    Curated(
        "mslearn-inventory-management",
        "learn.wwl.describe-inventory-management-supply-chain-management",
        ("warehouse-management",),
        2,
    ),
    Curated(
        "mslearn-quality-management",
        "learn-dynamics.configure-work-with-quality-control-in-dynamics-365-finance-ops",
        ("quality-management",),
        2,
    ),
    Curated(
        "mslearn-iot-customer-service",
        "learn-dynamics.connected-customer-service",
        ("iot-systems", "crm-systems"),
        2,
    ),
    Curated(
        "mslearn-customer-knowledge",
        "learn-bizapps.consuming-knowledge-articles-for-case-resolutions",
        ("customer-service", "crm-systems"),
        2,
    ),
    Curated(
        "mslearn-ai-case-management",
        "learn-dynamics.configure-copilot",
        ("customer-service", "conversational-ai"),
        2,
    ),
    Curated(
        "mslearn-responsible-copilot",
        "learn.github.responsible-ai-with-github-copilot",
        ("ai-ethics", "human-ai-collaboration"),
        1,
    ),
    Curated(
        "mslearn-responsible-ai-approach",
        "learn.philanthropies.introduction-to-microsofts-responsible-ai-approach",
        ("ai-ethics",),
        2,
    ),
    Curated(
        "mslearn-ai-privacy",
        "learn.wwl.privacy-security-responsible-ai-practices",
        ("data-privacy", "ai-ethics"),
        2,
    ),
    Curated(
        "mslearn-agent-governance",
        "learn.wwl.scale-responsible-ai-governance-multi-agent",
        ("ai-ethics", "data-governance-ai"),
        2,
    ),
    Curated(
        "mslearn-responsible-ai-teaching",
        "learn.philanthropies.apply-responsible-ai-principles",
        ("teaching-facilitation", "ai-ethics"),
        2,
    ),
    Curated(
        "mslearn-instructional-materials",
        "learn.mec.create-instructional-materials-teach-microsoft-365-copilot",
        ("instructional-design", "content-creation"),
        2,
    ),
    Curated(
        "mslearn-digital-twins",
        "learn.azure.connect-iot-hololens-azure-digital-twins-unity",
        ("digital-twin", "iot-systems"),
        2,
    ),
    Curated(
        "mslearn-manufacturing-overview",
        "learn-bizapps.manufacturing-overview",
        ("industrial-automation",),
        1,
    ),
    Curated(
        "mslearn-manufacturing-execution",
        "learn-dynamics.work-with-manufacturing-execution",
        ("industrial-automation",),
        2,
    ),
    Curated(
        "mslearn-privacy-risk",
        "learn.wwl.priva-privacy-risk-management",
        ("data-privacy", "data-governance-ai"),
        2,
    ),
    Curated(
        "mslearn-demand-forecasting",
        "learn-dynamics.forecast-using-demand-planning",
        ("time-series-forecasting", "logistics-planning"),
        2,
    ),
    Curated(
        "mslearn-health-interoperability",
        "learn-bizapps.healthcare-integration-interoperability",
        ("healthcare-informatics",),
        2,
    ),
    Curated(
        "mslearn-healthcare-overview", "learn-bizapps.healthcare-overview", ("healthcare-ai",), 1
    ),
    Curated("mslearn-iot-foundations", "learn.oxford.intro-to-iot-hub", ("iot-systems",), 1),
    Curated(
        "mslearn-data-pipelines",
        "learn.wwl.design-implement-data-pipelines",
        ("data-pipelines",),
        2,
    ),
    Curated(
        "mslearn-agentic-foundations",
        "learn.github.foundations-agentic-ai",
        ("ai-agents", "human-ai-collaboration"),
        1,
    ),
    Curated("mslearn-rag-foundations", "learn.wwl.rag-fundamentals", ("rag-systems",), 1),
    Curated(
        "mslearn-rag-databricks",
        "learn.wwl.retrieval-augmented-generation-azure-databricks",
        ("rag-systems", "vector-databases"),
        2,
    ),
    Curated(
        "mslearn-genai-evaluation",
        "learn.azure-evaluate-generative-ai-apps",
        ("llm-evaluation", "model-monitoring"),
        2,
    ),
)


@dataclass(frozen=True)
class CourseRow:
    id: str
    title: str
    provider: str
    url: str
    hours: float
    cost_myr: float
    hrd_claimable: bool
    verified_at: date
    skill_ids: tuple[str, ...]
    level: int
    source_name: str
    source_url: str
    hrd_note: str = ""
    language: str = "en"
    duration_note: str = ""
    provider_ref: str = ""
    # How it is delivered and sold (used by catalogue filters and the org plan).
    format: str = "self_paced"  # self_paced | live_online | in_person | hybrid | subscription
    audience: str = "individual"  # individual | corporate | both
    price_basis: str = "per_course"  # per_course | per_user_year | per_user_month | per_group
    currency: str = "MYR"  # currency of the provider's list price
    list_price: float | None = None  # in `currency`; cost_myr is the ringgit equivalent
    provider_type: str = "private_provider"
    location: str = ""
    price_note: str = ""


_COURSERA_FREE = (
    'Course page says "Enroll for free"; graded work and the certificate need a paid '
    "Certificate experience or Coursera Plus. Not HRD Corp claimable."
)


def _coursera(
    slug: str,
    title: str,
    partner: str,
    hours: float,
    skill: str,
    level: int,
    stated: str,
    checked: date = CHECKED,
) -> CourseRow:
    url = f"https://www.coursera.org/learn/{slug}"
    return CourseRow(
        id=f"coursera-{slug}",
        title=title,
        provider=f"Coursera ({partner})",
        url=url,
        hours=hours,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=checked,
        skill_ids=(skill,),
        level=level,
        source_name="Coursera course page",
        source_url=url,
        hrd_note=_COURSERA_FREE,
        duration_note=f"Sum of module hours on the course page ({hours:g} h); page states "
        f'"{stated}".',
        provider_ref=slug,
        provider_type="mooc",
    )


# Free-to-enrol Coursera courses, checked on their pages on CHECKED.
COURSERA: tuple[CourseRow, ...] = (
    _coursera("excel-basics-data-analysis-ibm", "Excel Basics for Data Analysis", "IBM", 13,
              "excel", 2, "1 week at 10 hours a week"),
    _coursera("python", "Programming for Everybody (Getting Started with Python)",
              "University of Michigan", 17, "python", 2, "2 weeks at 10 hours a week"),
    _coursera("sql-for-data-science", "SQL for Data Science", "University of California, Davis",
              15, "sql", 3, "2 weeks at 10 hours a week"),
    _coursera("prompt-engineering", "Prompt Engineering for ChatGPT", "Vanderbilt University",
              18, "prompt-engineering", 3, "2 weeks at 10 hours a week"),
    _coursera("supply-chain-logistics", "Supply Chain Logistics", "Rutgers University", 10,
              "logistics-planning", 2, "1 week at 10 hours a week"),
    # Checked 2026-10-23: each page shows "Enroll for free"; hours = sum of module hours.
    *(
        _coursera(slug, title, partner, hours, skill, level, stated, CHECKED_2)
        for slug, title, partner, hours, skill, level, stated in (
            ("machine-learning", "Supervised Machine Learning: Regression and Classification",
             "DeepLearning.AI and Stanford Online", 33, "machine-learning", 2,
             "3 weeks at 10 hours a week"),
            ("foundations-data", "Foundations: Data, Data, Everywhere", "Google", 13,
             "statistics", 1, "1 week at 10 hours a week"),
            ("foundations-of-cybersecurity", "Foundations of Cybersecurity", "Google", 10,
             "cybersecurity-operations", 2, "1 week at 10 hours a week"),
            ("renewable-energy-technology-fundamentals",
             "Renewable Energy Technology Fundamentals", "University of Colorado Boulder", 13,
             "renewable-energy-systems", 2, "1 week at 10 hours a week"),
            ("project-management-foundations", "Foundations of Project Management", "Google",
             12, "project-management", 2, "4 modules: 2, 4, 3 and 3 hours"),
            ("foundations-user-experience-design", "Foundations of User Experience (UX) Design",
             "Google", 12, "ux-design", 2, "4 modules: 4, 2, 4 and 2 hours"),
            ("foundations-of-digital-marketing-and-e-commerce",
             "Foundations of Digital Marketing and E-commerce", "Google", 11,
             "digital-marketing", 2, "4 modules: 3, 3, 3 and 2 hours"),
            ("introduction-to-cloud", "Introduction to Cloud Computing", "IBM", 13,
             "cloud-computing", 2, "5 weeks of study, ~2 hours/week"),
            ("cloud-computing-foundations-duke", "Cloud Computing Foundations",
             "Duke University", 35, "cloud-computing", 3, "4 weeks at 10 hours a week"),
            ("basic-statistics", "Basic Statistics", "University of Amsterdam", 17,
             "statistics", 3, "2 weeks at 10 hours a week"),
            ("iot", "Introduction to the Internet of Things and Embedded Systems",
             "University of California, Irvine", 12, "iot-systems", 2, "4 weeks, 1-3 hours/week"),
            ("business-analysis-fundamentals", "Business Analysis Fundamentals", "Microsoft",
             18, "business-analysis", 2, "2 weeks at 10 hours a week"),
            ("instructional-design-foundations-applications",
             "Instructional Design Foundations and Applications",
             "University of Illinois Urbana-Champaign", 13, "instructional-design", 2,
             "1 week at 10 hours a week"),
            ("html-css-javascript-for-web-developers",
             "HTML, CSS, and Javascript for Web Developers", "Johns Hopkins University", 4,
             "software-development", 1, "one 4-hour module"),
            ("financial-accounting-basics", "Financial Accounting: Foundations",
             "University of Illinois Urbana-Champaign", 12, "accounting-reporting", 2,
             "4 weeks of study, 4-6 hours/week"),
            ("introduction-to-data-engineering", "Introduction to Data Engineering", "IBM", 14,
             "data-pipelines", 2, "4 modules: 2, 5, 4 and 3 hours"),
            ("cybersecurity-for-everyone", "Cybersecurity for Everyone",
             "University of Maryland, College Park", 22, "cybersecurity-governance", 2,
             "6 modules totalling 22 hours"),
            ("agile-project-management", "Agile Project Management", "Google", 20,
             "project-management", 3, "4 modules: 4, 2, 9 and 5 hours"),
            ("sales-strategy", "Sales Strategy", "Fundação Instituto de Administração (FIA)", 16,
             "sales-account-management", 3, "2 weeks at 10 hours a week (intermediate level)"),
            ("social-media-marketing", "Social Media Marketing", "SkillUp", 13,
             "content-creation", 2, "4 weeks of study, 2-4 hours/week"),
            ("inventory-management", "Inventory Management", "University of California, Irvine",
             4, "warehouse-management", 2, "4 modules of 1 hour (page: 5 hours to complete)"),
            ("salesforce-fundamentals", "Salesforce Basics", "University of California, Irvine",
             5, "crm-systems", 2, "3 weeks of study, 3-5 hours/week"),
            ("semiconductor-physics", "Semiconductor Physics", "University of Colorado Boulder",
             15, "semiconductor-process", 2, "2 weeks at 10 hours a week (advanced level)"),
            ("hotel-distribution", "The fundamentals of hotel distribution",
             "ESSEC Business School", 18, "tourism-hospitality", 2, "4 weeks, 2-4 hours/week"),
            ("six-sigma-define-measure-advanced", "Six Sigma Advanced Define and Measure Phases",
             "Kennesaw State University", 12, "quality-management", 3,
             "7 modules totalling 12 hours (intermediate level)"),
        )
    ),
)  # fmt: skip

_TWO_DAYS = "Brochure states 2 days; 14 h assumes 7 h/day, the HRD Corp maximum session length."
_UNIMAS_PDF = (
    "https://www.business.unimas.my/images/2026/TrainingShortCourse/updateAug/Excel-T5.pdf"
)
_FMM_PDF = (
    "https://old.fmm.org.my/images/articles/training/SUPPLY%20CHAIN%20AND%20LOGISTIC%20"
    "MANAGEMENT.pdf"
)
_MAICSA_PDF = "https://maicsa.org.my/media/training_calendar/cs111224w1.pdf"
_FMM_POWERBI_PDF = "https://smtp.fmm.org.my/images/articles/training/15431Brochure.pdf"

# Foreign-currency prices are converted at Bank Negara Malaysia's selling rate (what a buyer
# of the currency pays). Seed files use the reading below; live sync replaces it daily.
BNM_FX_API = "https://api.bnm.gov.my/public/exchange-rate/{currency}"
BNM_SOURCE = "Bank Negara Malaysia OpenAPI (exchange rates)"
SEED_USD_RATE = 4.088
SEED_USD_RATE_DATE = date(2026, 10, 19)


def usd_to_myr(amount: float, rate: float = SEED_USD_RATE) -> float:
    return round(amount * rate, 2)


def fx_note(amount: float, rate: float = SEED_USD_RATE, on: date = SEED_USD_RATE_DATE) -> str:
    return (
        f"Listed as USD {amount:g}; RM {usd_to_myr(amount, rate):,.2f} at the Bank Negara "
        f"Malaysia selling rate of {rate:g} on {on.isoformat()}."
    )


# Paid, HRD Corp-claimable courses checked by hand on the provider's own page or brochure.
MANUAL: tuple[CourseRow, ...] = (
    CourseRow(
        id="aitraining2u-ai-data-analytics",
        format="in_person",
        audience="both",
        provider_type="private_provider",
        location="Kuala Lumpur",
        title="AI Data Analytics Training (2 days)",
        provider="AITraining2U",
        url="https://www.aitraining2u.com/aianalytics.html",
        hours=14,
        cost_myr=3500,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("sql", "python", "data-visualisation"),
        level=3,
        source_name="Provider course page",
        source_url="https://www.aitraining2u.com/aianalytics.html",
        hrd_note=(
            "Provider page states the course is 100% HRDC claimable (SBL-KHAS) for eligible "
            "Malaysian employers; HRDC-claimable fee RM3,500, self-funded RM3,200, both before "
            "8% SST. The employer applies for the grant before the course starts."
        ),
        duration_note=(
            "Page states 2 days; 14 h assumes 7 h/day, the HRD Corp maximum session length. "
            "2026 intake dates to be confirmed by the provider."
        ),
    ),
    CourseRow(
        id="aitraining2u-chatgpt",
        format="in_person",
        audience="both",
        provider_type="private_provider",
        location="Kuala Lumpur",
        title="ChatGPT Training: Custom GPTs, Agents & Codex (2 days)",
        provider="AITraining2U",
        url="https://www.aitraining2u.com/chatgpt-training-malaysia.html",
        hours=14,
        cost_myr=3500,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("prompt-engineering", "ai-literacy"),
        level=3,
        source_name="Provider course page",
        source_url="https://www.aitraining2u.com/chatgpt-training-malaysia.html",
        hrd_note=(
            'Provider page: "claimable under the SBL-KHAS scheme for eligible Malaysian '
            'employers"; HRDC-claimable RM3,500 + 8% SST (self-funded RM3,200 + SST). '
            "Participants need their own ChatGPT Plus seat."
        ),
        duration_note=_TWO_DAYS.replace("Brochure", "Page") + " Dates: coming soon.",
    ),
    CourseRow(
        id="unimas-excel-booster",
        format="in_person",
        audience="both",
        provider_type="university",
        location="Kuching / Miri, Sarawak",
        title="Booster with #ExcelChampMY (Microsoft Excel, Intermediate)",
        provider="UNIMAS (PROCEL)",
        url=_UNIMAS_PDF,
        hours=14,
        cost_myr=1100,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("excel",),
        level=3,
        source_name="UNIMAS training brochure (PDF)",
        source_url=_UNIMAS_PDF,
        hrd_note=(
            'Brochure: "RM 1,100 / pax (Approved for HRDC Grant Application under SBL-Khas '
            'Scheme)"; "HRDC SBL-KHAS scheme, NO upfront payment"; 8% SST added on the form.'
        ),
        duration_note=(
            "2 days, 8:30 a.m.-5:00 p.m.; 14 h assumes 7 h/day. Listed runs (Miri 4-5 Aug, "
            "Kuching 7-8 Sep 2026) have passed: ask the provider for new dates."
        ),
    ),
    CourseRow(
        id="unimas-excel-powering-up",
        format="in_person",
        audience="both",
        provider_type="university",
        location="Kuching / Miri, Sarawak",
        title="Powering Up with #ExcelChampMY (Microsoft Excel, Advance)",
        provider="UNIMAS (PROCEL)",
        url=_UNIMAS_PDF,
        hours=14,
        cost_myr=1300,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("excel",),
        level=4,
        source_name="UNIMAS training brochure (PDF)",
        source_url=_UNIMAS_PDF,
        hrd_note=(
            'Brochure: "RM 1,300 / pax (Approved for HRDC Grant Application under SBL-Khas '
            'Scheme)"; 8% SST added on the form.'
        ),
        duration_note=(
            "2 days, 8:30 a.m.-5:00 p.m.; 14 h assumes 7 h/day. Listed runs (Miri 6-7 Aug, "
            "Kuching 14-15 Sep 2026) have passed: ask the provider for new dates."
        ),
    ),
    CourseRow(
        id="fmm-supply-chain-logistics",
        format="in_person",
        audience="both",
        provider_type="industry_body",
        location="Kuching, Sarawak",
        title="Supply Chain and Logistics Management (2 days)",
        provider="FMM Institute (Sarawak Branch)",
        url=_FMM_PDF,
        hours=14,
        cost_myr=1350,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("logistics-planning",),
        level=3,
        source_name="FMM training brochure (PDF)",
        source_url=_FMM_PDF,
        hrd_note=(
            'Listed under "HRD Corp Claimable Courses"; the form offers "We will be claiming '
            'from HRD Corp". Non-member RM1,350 (member RM1,134), inclusive of 8% service tax.'
        ),
        duration_note=(
            "2 days, 8:30 a.m.-4:30 p.m.; 14 h assumes 7 h/day. Listed run (15-16 Jan 2026, "
            "Kuching) has passed: ask FMM for new dates."
        ),
    ),
    CourseRow(
        id="maicsa-aml-str",
        format="live_online",
        audience="both",
        provider_type="professional_body",
        location="Online",
        title="AML/CFT Webinar Series: Suspicious Transaction Report (STR)",
        provider="MAICSA",
        url=_MAICSA_PDF,
        hours=4,
        cost_myr=490,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("risk-compliance",),
        level=2,
        source_name="MAICSA training brochure (PDF)",
        source_url=_MAICSA_PDF,
        hrd_note=(
            "Brochure carries the HRD Corp Claimable mark (SBL-Khas remote online training); "
            '"Registration with HRDCorp grant, the NORMAL FEE will apply": RM490 non-member.'
        ),
        duration_note=(
            "Virtual, 9:00 a.m.-1:00 p.m. (4 CPD hours). Listed run (11 Dec 2024) has passed: "
            "check MAICSA's training calendar for the next one."
        ),
    ),
    CourseRow(
        id="ukm-data-analytics-certificate",
        title="Professional Certificate in Data Analytics",
        provider="Universiti Kebangsaan Malaysia (UKMSHAPE)",
        url="https://www.ukm.my/studyukm/professional-certificate-in-data-analytics/",
        hours=160,
        cost_myr=3000,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("python", "data-visualisation"),
        level=3,
        source_name="UKM programme page",
        source_url="https://www.ukm.my/studyukm/professional-certificate-in-data-analytics/",
        hrd_note=(
            'Programme page: "this course is claimable under HRD Corp"; the employer must be '
            "registered, contributing and submit the claim. RM 3,000 for Malaysian applicants."
        ),
        duration_note=(
            "3 months, 4 credits, online on weekends. 160 h applies the MQA rule of 40 notional "
            "learning hours per credit. Covers Python (Jupyter), Tableau and Power BI."
        ),
        format="live_online",
        audience="both",
        provider_type="university",
        location="Online",
    ),
    CourseRow(
        id="fmm-power-bi",
        title="Power BI: Data Visualisation & Business Intelligence (2 days)",
        provider="FMM Institute (Eastern Branch)",
        url=_FMM_POWERBI_PDF,
        hours=14,
        cost_myr=1080,
        hrd_claimable=True,
        verified_at=CHECKED,
        skill_ids=("data-visualisation",),
        level=3,
        source_name="FMM training brochure (PDF)",
        source_url=_FMM_POWERBI_PDF,
        hrd_note=(
            'Brochure section "HRD CORP CLAIMABLE COURSE DETAILS" (FMM Institute Eastern); '
            "non-member RM1,080, member RM972, inclusive of 8% SST."
        ),
        duration_note=(
            "2 days, 9 a.m.-5 p.m.; 14 h assumes 7 h/day. Listed run (11-12 Feb 2026) has "
            "passed: ask FMM for new dates."
        ),
        format="in_person",
        audience="both",
        provider_type="industry_body",
        location="FMM Eastern Branch",
    ),
    CourseRow(
        id="utm-registered-energy-manager-type1",
        title="Registered Energy Manager (REM) - Type 1 Training (5 days)",
        provider="UTMSPACE with UTM PROSPECT",
        url="https://research.utm.my/prospect/registered-energy-manager-rem-type-1-training/",
        hours=35,
        cost_myr=4900,
        hrd_claimable=True,
        verified_at=CHECKED_2,
        skill_ids=("energy-efficiency",),
        level=3,
        source_name="UTM course page",
        source_url="https://research.utm.my/prospect/registered-energy-manager-rem-type-1-training/",
        hrd_note=(
            'Course page: "HRD Corp Claimable"; "RM 4,900 per participant (HRDC claimable '
            'rate)", "RM 4,600 per participant (normal rate)". For professionals seeking REM '
            "certification under Suruhanjaya Tenaga (Energy Efficiency and Conservation Act)."
        ),
        duration_note=(
            "5 days full time at UTMSPACE Johor Bahru; 35 h assumes 7 h/day. The listed run "
            "(10-14 Nov 2025) has passed: ask UTMSPACE for the next intake."
        ),
        format="in_person",
        audience="both",
        provider_type="university",
        location="Johor Bahru",
    ),
    CourseRow(
        id="ibfim-fundamentals-shariah-islamic-finance",
        title="Fundamentals of Shariah for Islamic Finance (FCIBT Module 1)",
        provider="IBFIM",
        url="https://ibfimonline.com/wp-content/uploads/2022/12/brochure/10-FCIBT.pdf",
        hours=21,
        cost_myr=2730,
        hrd_claimable=True,
        verified_at=CHECKED_2,
        skill_ids=("islamic-finance",),
        level=2,
        source_name="IBFIM FCIBT brochure (PDF, Version 1.0)",
        source_url="https://ibfimonline.com/wp-content/uploads/2022/12/brochure/10-FCIBT.pdf",
        hrd_note=(
            'Brochure: "HRDC - All the programme listed are HRDC claimable"; module fee MYR '
            "2,730 online (MYR 3,450 face-to-face), subject to SST; assessment MYR 100."
        ),
        duration_note=(
            "21 hours (3 days) per module, online or face-to-face; entry requirement SPM. "
            "Brochure dated 2022 (6% SST): confirm the current fee with IBFIM."
        ),
        format="live_online",
        audience="both",
        provider_type="professional_body",
        location="Online / Kuala Lumpur",
    ),
    # Bahasa Melayu, paid and HRD Corp-claimable (page read on CHECKED_3).
    CourseRow(
        id="modernlms-kursus-google-ads-ms",
        title="Kursus Google Ads",
        provider="ModernLMS",
        url="https://www.modernlms.com/learning/courses/kursus-google-ads/",
        hours=4,
        cost_myr=149,
        hrd_claimable=True,
        verified_at=CHECKED_3,
        skill_ids=("digital-marketing",),
        level=2,
        source_name="Provider course page",
        source_url="https://www.modernlms.com/learning/courses/kursus-google-ads/",
        hrd_note=(
            "Provider page lists the e-certificate of completion as HRD Corp claimable; fee "
            "RM 149.00. Google's own Google Ads Certification Exam is separate and not included."
        ),
        language="ms",
        duration_note="Page states 4 hours, Bahasa Melayu, 12 modules, 1 year of access.",
        provider_ref="kursus-google-ads",
        format="self_paced",
        audience="both",
        list_price=149,
        provider_type="private_provider",
        location="Online",
    ),
)

FREE_DIGITAL: tuple[CourseRow, ...] = (
    CourseRow(
        id="mslearn-intro-git",
        title="Introduction to Git",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/modules/intro-to-git/",
        hours=1.4,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=CHECKED_3,
        skill_ids=("git",),
        level=2,
        source_name="Microsoft Learn course page",
        source_url="https://learn.microsoft.com/en-us/training/modules/intro-to-git/",
        hrd_note="Free learning module; nothing to claim. GitHub account required.",
        language="en",
        duration_note=(
            "86 minutes across 6 units, rounded to 1.4 hours; "
            "GitHub account and CLI familiarity required."
        ),
        provider_ref="intro-to-git",
        format="self_paced",
        audience="both",
        provider_type="mooc",
        location="Online",
    ),
    CourseRow(
        id="mslearn-cloud-ai-postgresql",
        title=(
            "Integrate AI services to enrich your applications with intelligent features in "
            "Azure Database for PostgreSQL"
        ),
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/modules/integrate-ai-services-enrich-azure-database-postgresql/",
        hours=1.2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("cloud-ai-services",),
        level=3,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/modules/integrate-ai-services-enrich-azure-database-postgresql/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 72 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.wwl.integrate-ai-services-enrich-azure-database-postgresql",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. Azure AI Language, Translator and ML endpoint "
            "integration; SQL and Azure provisioning prerequisites."
        ),
    ),
    CourseRow(
        id="mslearn-architecture-infrastructure",
        title="AZ-305: Design infrastructure solutions",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/paths/design-infranstructure-solutions/",
        hours=3.6,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("enterprise-architecture",),
        level=3,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/paths/design-infranstructure-solutions/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 219 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.wwl.design-infranstructure-solutions",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. Compute, application, network and migration "
            "architecture; partial systems-design coverage, not a complete enterprise "
            "architecture qualification."
        ),
    ),
    CourseRow(
        id="mslearn-evaluate-genai-safety",
        title="Evaluate generative AI applications",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/paths/evaluate-generative-ai-apps/",
        hours=1.6,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("ai-safety",),
        level=2,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/paths/evaluate-generative-ai-apps/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 96 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.azure-evaluate-generative-ai-apps",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. Risk and safety metrics, evaluation SDK and "
            "synthetic evaluation datasets; requires Python, Azure and GitHub."
        ),
    ),
    CourseRow(
        id="mslearn-security-copilot-operations",
        title="Enhance security operations by using Microsoft Security Copilot",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/paths/security-copilot-and-ai/",
        hours=6.2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("security-ai",),
        level=2,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/paths/security-copilot-and-ai/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 372 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.wwl.security-copilot-and-ai",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. AI-assisted security analysis and response; "
            "requires security operations and Microsoft security product knowledge."
        ),
    ),
    CourseRow(
        id="mslearn-ai-business-strategy",
        title="Transform your business with AI",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/paths/transform-your-business-with-microsoft-ai/",
        hours=2.6,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("ai-product-management",),
        level=2,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/paths/transform-your-business-with-microsoft-ai/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 154 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.wwl.transform-your-business-with-microsoft-ai",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. AI value identification, project strategy, "
            "responsibility and scaling; introductory product-lifecycle coverage."
        ),
    ),
    CourseRow(
        id="mslearn-ai-compliance-design",
        title="Design responsible AI security, governance, risk management, and compliance",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/modules/design-responsible-ai-security-governance-risk-management-compliance/",
        hours=0.9,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("regulatory-affairs",),
        level=3,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/modules/design-responsible-ai-security-governance-risk-management-compliance/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 53 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.wwl.design-responsible-ai-security-governance-risk-management-compliance",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. Translates compliance requirements into "
            "technical AI controls; does not qualify the learner in Malaysian law or "
            "regulatory practice."
        ),
    ),
    CourseRow(
        id="mslearn-digital-learning-design",
        title="21st century learning design",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/paths/21st-century-learning-design/",
        hours=6.7,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("learning-development",),
        level=2,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/paths/21st-century-learning-design/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 401 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn.mec.21st-century-learning-design",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. Design and redesign learning activities with "
            "digital tools and rubrics; educator-focused foundation, not a complete corporate "
            "L&D programme qualification."
        ),
    ),
    CourseRow(
        id="mslearn-ai-workforce-planning",
        title="Optimize staffing with workforce management in Dynamics 365 Contact Center",
        provider="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/training/modules/optimize-staffing-workforce-management-contact-center/",
        hours=0.7,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("workforce-planning",),
        level=2,
        source_name="Microsoft Learn course page and Catalog API",
        source_url="https://learn.microsoft.com/en-us/training/modules/optimize-staffing-workforce-management-contact-center/",
        hrd_note="Free self-paced learning; nothing to claim.",
        language="en",
        duration_note=(
            "Microsoft Learn Catalog API lists 42 minutes; rounded to one decimal hour. Page "
            "and API opened 2026-10-31."
        ),
        provider_ref="learn-dynamics.optimize-staffing-workforce-management-contact-center",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "RM0 covers learning content. Azure resource usage or licensed product access can "
            "cost extra; exams are separate. AI-based demand forecasting, capacity and shift "
            "planning in a contact centre; limited domain coverage, human staffing decisions "
            "remain required."
        ),
    ),
    CourseRow(
        id="kaggle-advanced-sql",
        title="Advanced SQL",
        provider="Kaggle Learn",
        url="https://www.kaggle.com/learn/advanced-sql/course",
        hours=4,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("sql-advanced",),
        level=3,
        source_name="Kaggle Learn course page",
        source_url="https://www.kaggle.com/learn/advanced-sql/course",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note="Provider estimates 4 hours.",
        provider_ref="kaggle-advanced-sql",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "No cost for Kaggle Learn courses. No professional certification entitlement "
            "assumed. Window functions, nested data, joins and efficient BigQuery queries; "
            "assumes Intro to SQL."
        ),
    ),
    CourseRow(
        id="kaggle-ml-explainability",
        title="Machine Learning Explainability",
        provider="Kaggle Learn",
        url="https://www.kaggle.com/learn/machine-learning-explainability/course",
        hours=4,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("explainable-ai",),
        level=3,
        source_name="Kaggle Learn course page",
        source_url="https://www.kaggle.com/learn/machine-learning-explainability/course",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note="Provider estimates 4 hours.",
        provider_ref="kaggle-ml-explainability",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "No cost for Kaggle Learn courses. No professional certification entitlement "
            "assumed. Permutation importance, partial dependence and SHAP; assumes "
            "introductory machine learning."
        ),
    ),
    CourseRow(
        id="kaggle-ai-ethics-bias",
        title="Intro to AI Ethics",
        provider="Kaggle Learn",
        url="https://www.kaggle.com/learn/intro-to-ai-ethics/course",
        hours=4,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("bias-auditing",),
        level=2,
        source_name="Kaggle Learn course page",
        source_url="https://www.kaggle.com/learn/intro-to-ai-ethics/course",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note="Provider estimates 4 hours.",
        provider_ref="kaggle-ai-ethics-bias",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "No cost for Kaggle Learn courses. No professional certification entitlement "
            "assumed. Bias identification, fairness measures and model cards with practical "
            "examples; introductory auditing coverage."
        ),
    ),
    CourseRow(
        id="cfte-ai-finance-masterclass",
        title="AI in Finance Masterclass",
        provider="CFTE",
        url="https://courses.cfte.education/online-artificial-intelligence-in-finance-masterclass-learn-ai-for-free/",
        hours=0.8,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("fintech-ai",),
        level=1,
        source_name="CFTE course page",
        source_url="https://courses.cfte.education/online-artificial-intelligence-in-finance-masterclass-learn-ai-for-free/",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note=(
            "FAQ and free-masterclass panel specify about 45 minutes (0.8 hours rounded). "
            "Hero also says under 2 hours; use the more specific masterclass duration."
        ),
        provider_ref="cfte-ai-finance-masterclass",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "Provider explicitly confirms free immediate access without payment details. No "
            "professional certification entitlement assumed. AI use cases in financial "
            "services, risk and governance; introductory awareness, not algorithmic-trading "
            "proficiency."
        ),
    ),
    CourseRow(
        id="openlearn-energy-financial-modelling",
        title="Financial Modelling for Energy Transitions MINFin, FinTrack & FinCoRE",
        provider="OpenLearn Create (Climate Compatible Growth)",
        url="https://www.open.edu/openlearncreate/course/view.php?id=17735",
        hours=15,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("financial-analysis",),
        level=3,
        source_name="OpenLearn Create (Climate Compatible Growth) course page",
        source_url="https://www.open.edu/openlearncreate/course/view.php?id=17735",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note="Provider lists 15 hours study and intermediate level.",
        provider_ref="openlearn-energy-financial-modelling",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "Provider confirms free learning and participation statement. No professional "
            "certification entitlement assumed. Excel cashflow models, climate finance gaps "
            "and cost of capital; general financial-modelling coverage, not Islamic finance "
            "certification."
        ),
    ),
    CourseRow(
        id="eit-precision-farming-basics",
        title="Precision Farming ? Basics",
        provider="28DIGITAL (Agri-Digital Growth consortium)",
        url="https://28digital.ea.education/courses/precision-farming-basics/",
        hours=48,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("precision-agriculture",),
        level=2,
        source_name="28DIGITAL (Agri-Digital Growth consortium) course page",
        source_url="https://eit-campus.eu/course/digital/precision-farming-basics",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note=(
            "EIT Campus lists 20-48 hours; 48 hours is the upper-bound planning estimate, not "
            "an exact provider duration."
        ),
        provider_ref="eit-precision-farming-basics",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "EIT Campus and enrolment page both list Free. No professional certification "
            "entitlement assumed. Precision farming, field data, sensors, robotics and AI in "
            "agriculture; introductory skill estimate despite intermediate provider "
            "classification."
        ),
    ),
    CourseRow(
        id="ecmwf-ml-earth-systems-applications",
        title="Machine Learning for Earth Systems Modelling - Course 3",
        provider="ECMWF",
        url="https://learning.ecmwf.int/course/view.php?id=100",
        hours=24,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("climate-ai",),
        level=3,
        source_name="ECMWF course page",
        source_url="https://learning.ecmwf.int/tag/index.php?tag=Machine+learning&tc=2",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note=(
            "Provider lists approximately 16-24 hours; 24 hours is the upper-bound planning "
            "estimate."
        ),
        provider_ref="ecmwf-ml-earth-systems-applications",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "Provider catalogue states free participation open to anyone meeting "
            "prerequisites. No professional certification entitlement assumed. ML workflows "
            "for weather/climate, downscaling and coupled Earth systems. Advanced Python/ML "
            "and Earth-system knowledge required; not a beginner farming course."
        ),
    ),
    CourseRow(
        id="freecodecamp-selenium-bot",
        title="Use Selenium to Create a Web Scraping Bot",
        provider="freeCodeCamp",
        url="https://www.freecodecamp.org/news/use-selenium-to-create-a-web-scraping-bot/",
        hours=3,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 31),
        skill_ids=("selenium",),
        level=2,
        source_name="freeCodeCamp course page",
        source_url="https://www.freecodecamp.org/news/use-selenium-to-create-a-web-scraping-bot/",
        hrd_note="Free learning; no HRD Corp reimbursement assumed.",
        language="en",
        duration_note="Provider course page states a 3-hour watch; practice time is additional.",
        provider_ref="freecodecamp-selenium-bot",
        format="self_paced",
        audience="both",
        price_basis="per_course",
        currency="MYR",
        list_price=None,
        provider_type="mooc",
        location="Online",
        price_note=(
            "Public course video and transcript are freely accessible. No professional "
            "certification entitlement assumed. Selenium browser automation, selectors, waits "
            "and project structure; assumes Python. Published 2021; learners must check "
            "current Selenium API compatibility."
        ),
    ),
)

# Free Bahasa Melayu courses (language="ms", the existing catalogue language code).
# Pages read on CHECKED_3; a locale in a URL alone does not verify the teaching language.
FREE_MS: tuple[CourseRow, ...] = (
    CourseRow(
        id="pepperlabs-ai-ready-pendidik-ms",
        title="AI Ready Malaysia: Edisi Pendidik",
        provider="Pepper Labs (AVPN AI Opportunity Fund)",
        url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pendidik",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=CHECKED_3,
        skill_ids=("ai-literacy", "prompt-engineering"),
        level=2,
        source_name="Pepper Labs course page",
        source_url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pendidik",
        hrd_note="Free to enrol; nothing to claim.",
        language="ms",
        duration_note=(
            "Page states about 2 hours of video content in 51 lessons; curriculum "
            "sections and lesson titles are in Bahasa Melayu. Page does not mention a certificate."
        ),
        provider_ref="ai-ready-malaysia-asia-pacific-edisi-pendidik",
        format="self_paced",
        audience="individual",
        provider_type="mooc",
        location="Online",
    ),
    CourseRow(
        id="pepperlabs-ai-ready-msme-ms",
        title="AI Ready Malaysia: Edisi Tenaga Kerja MSME",
        provider="Pepper Labs (AVPN AI Opportunity Fund)",
        url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-tenaga-kerja-MSME",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=CHECKED_3,
        skill_ids=("ai-literacy", "prompt-engineering", "ai-ethics"),
        level=2,
        source_name="Pepper Labs course page",
        source_url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-tenaga-kerja-MSME",
        hrd_note="Free to enrol; nothing to claim.",
        language="ms",
        duration_note=(
            "Page states about 2 hours of video content in 43 lessons; curriculum "
            "sections and lesson titles are in Bahasa Melayu. Page does not mention a certificate."
        ),
        provider_ref="ai-ready-malaysia-asia-pacific-edisi-tenaga-kerja-MSME",
        format="self_paced",
        audience="both",
        provider_type="mooc",
        location="Online",
    ),
    CourseRow(
        id="pepperlabs-ai-ready-pelajar-ms",
        title="AI Ready Malaysia: Edisi Pelajar",
        provider="Pepper Labs (AVPN AI Opportunity Fund)",
        url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pelajar",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=CHECKED_3,
        skill_ids=("ai-literacy", "prompt-engineering"),
        level=2,
        source_name="Pepper Labs course page",
        source_url="https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pelajar",
        hrd_note="Free to enrol; nothing to claim.",
        language="ms",
        duration_note=(
            "Page states about 2 hours of video content in 44 lessons; curriculum "
            "sections and lesson titles are in Bahasa Melayu. Page does not mention a certificate."
        ),
        provider_ref="ai-ready-malaysia-asia-pacific-edisi-pelajar",
        format="self_paced",
        audience="individual",
        provider_type="mooc",
        location="Online",
    ),
    CourseRow(
        id="modernlms-kursus-excel-ms",
        title="Kursus Microsoft Excel",
        provider="ModernLMS",
        url="https://www.modernlms.com/learning/courses/kursus-microsoft-excel/",
        hours=2,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=CHECKED_3,
        skill_ids=("excel", "excel-basic"),
        level=1,
        source_name="Provider course page",
        source_url="https://www.modernlms.com/learning/courses/kursus-microsoft-excel/",
        hrd_note=(
            'Page lists the course as free and also shows an "HRD Corp claimable" tag; there '
            "is no fee to claim, so it is not treated as claimable."
        ),
        language="ms",
        duration_note=(
            "Page states 2 hours, Bahasa Melayu, fundamental level, 6 modules, 1 year of access."
        ),
        provider_ref="kursus-microsoft-excel",
        format="self_paced",
        audience="individual",
        provider_type="private_provider",
        location="Online",
    ),
)

# Subscriptions and corporate bundles: shown in the catalogue and to HR, never booked as a
# pathway step (they unlock courses rather than teach a skill themselves).
BUNDLES: tuple[CourseRow, ...] = (
    CourseRow(
        id="coursera-plus-annual",
        title="Coursera Plus (annual subscription)",
        provider="Coursera",
        url="https://www.coursera.org/courseraplus",
        hours=0.1,
        cost_myr=usd_to_myr(239),
        hrd_claimable=False,
        verified_at=CHECKED,
        skill_ids=tuple(sorted({s for r in COURSERA for s in r.skill_ids})),
        level=3,
        source_name="Coursera Plus page",
        source_url="https://www.coursera.org/courseraplus",
        hrd_note=(
            "Unlocks graded work and certificates for the Coursera courses in this catalogue "
            "(and 10,000+ others; some programmes excluded). Not HRD Corp claimable."
        ),
        duration_note="Subscription: hours depend on the courses taken.",
        format="subscription",
        audience="individual",
        price_basis="per_user_year",
        currency="USD",
        list_price=239,
        provider_type="mooc",
        location="Online",
        price_note=fx_note(239),
    ),
)


def clean_url(url: str) -> str:
    """Drop query and fragment (the API adds a tracking parameter)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def missing_curated(payload: dict[str, Any]) -> list[Curated]:
    """Curated Microsoft Learn items the catalogue no longer lists (retired)."""
    uids = {i["uid"] for key in ("modules", "learningPaths") for i in payload.get(key, [])}
    return [c for c in CURATED if c.uid not in uids]


def from_mslearn(
    payload: dict[str, Any], retrieved: date, allow_missing: bool = False
) -> list[CourseRow]:
    index = {i["uid"]: i for key in ("modules", "learningPaths") for i in payload.get(key, [])}
    missing = missing_curated(payload)
    if missing and not allow_missing:
        raise ValueError(
            f"curated UIDs not in the catalogue (retired?): {[c.uid for c in missing]}"
        )
    rows: list[CourseRow] = []
    for c in CURATED:
        item = index.get(c.uid)
        if item is None:
            continue
        minutes = int(item["duration_in_minutes"])
        if minutes <= 0:
            raise ValueError(f"{c.uid}: no duration")
        kind = "learning path" if item["type"] == "learningPath" else "module"
        rows.append(
            CourseRow(
                id=c.id,
                title=" ".join(str(item["title"]).split()),
                provider="Microsoft Learn",
                url=clean_url(item["url"]),
                hours=round(minutes / 60, 1),
                cost_myr=0,
                hrd_claimable=False,
                verified_at=retrieved,
                skill_ids=c.skill_ids,
                level=c.level,
                source_name=MSLEARN_SOURCE,
                source_url=MSLEARN_SOURCE_URL,
                hrd_note="Free; nothing to claim.",
                duration_note=f"Microsoft Learn {kind}, {minutes} min as listed by the provider.",
                provider_ref=c.uid,
                provider_type="mooc",
            )
        )
    return rows


def all_rows(
    payload: dict[str, Any], retrieved: date, allow_missing: bool = False
) -> list[CourseRow]:
    return (
        from_mslearn(payload, retrieved, allow_missing)
        + list(COURSERA)
        + list(MANUAL)
        + list(FREE_DIGITAL)
        + list(FREE_MS)
        + list(BUNDLES)
    )


def fetch_fx(
    currency: str, get_json: Callable[[str, int], Any] | None = None
) -> tuple[float, date]:
    """(MYR selling rate per 1 unit of `currency`, rate date) from Bank Negara Malaysia."""
    url = BNM_FX_API.format(currency=quote(currency))
    if get_json is None:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.BNM.API.v1+json", "User-Agent": "adept/1.0"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            body = json.load(r)
    else:
        body = get_json(url, 30)
    data = body["data"]
    rate = float(data["rate"]["selling_rate"]) / float(data.get("unit") or 1)
    return rate, date.fromisoformat(data["rate"]["date"])


def with_fx(rows: Iterable[CourseRow], rate: float, on: date) -> list[CourseRow]:
    """Re-price USD rows in ringgit at `rate` (MYR per USD) dated `on`."""
    out: list[CourseRow] = []
    for r in rows:
        if r.currency == "USD" and r.list_price is not None:
            r = replace(
                r,
                cost_myr=usd_to_myr(r.list_price, rate),
                price_note=fx_note(r.list_price, rate, on),
            )
        out.append(r)
    return out


def validate(rows: Iterable[CourseRow], skills: set[str]) -> None:
    rows = list(rows)
    ids = [r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate course ids")
    for r in rows:
        if not r.id.strip() or not r.title.strip() or not r.provider.strip():
            raise ValueError(f"{r.id}: missing course identity or provider")
        if not math.isfinite(r.cost_myr) or r.cost_myr < 0:
            raise ValueError(f"{r.id}: invalid cost")
        if not r.source_name.strip() or not r.source_url.startswith("https://"):
            raise ValueError(f"{r.id}: missing source attribution")
        if not isinstance(r.verified_at, date):
            raise ValueError(f"{r.id}: missing verification date")
        unknown = set(r.skill_ids) - skills
        if unknown:
            raise ValueError(f"{r.id}: unknown skill ids {sorted(unknown)}")
        if (
            not 1 <= r.level <= 5
            or not math.isfinite(r.hours)
            or r.hours <= 0
            or not r.url.startswith("https://")
        ):
            raise ValueError(f"{r.id}: invalid level, hours or url")
        if r.hrd_claimable and not r.hrd_note:
            raise ValueError(f"{r.id}: HRD Corp claim without the provider's statement")
        if r.currency != "MYR" and (r.list_price is None or not r.price_note):
            raise ValueError(f"{r.id}: foreign-currency price without list price and FX note")


def write_csv(rows: Iterable[CourseRow], out: Path) -> None:
    rows = list(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys())
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(fields)
        for r in rows:
            values = asdict(r)
            values["skill_ids"] = "{" + ",".join(r.skill_ids) + "}"
            values["hrd_claimable"] = "true" if r.hrd_claimable else "false"
            values["list_price"] = "" if r.list_price is None else r.list_price
            w.writerow([values[f] for f in fields])


def _get_json(url: str, timeout_s: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "adept-catalogue/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s, context=ssl.create_default_context()) as r:
        return json.load(r)


def fetch_mslearn(timeout_s: int = 120) -> dict[str, Any]:
    data: dict[str, Any] = _get_json(MSLEARN_API, timeout_s)
    return data


def coursera_status(slug: str, get_json: Callable[[str, int], Any] = _get_json) -> bool | None:
    """True if Coursera still lists the course, False if it is gone, None if unknown."""
    try:
        body = get_json(COURSERA_API.format(slug=quote(slug)), 20)
    except urllib.error.HTTPError as exc:
        return False if exc.code == 404 else None
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    return bool(body.get("elements"))
