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
    slug: str, title: str, partner: str, hours: float, skill: str, level: int, stated: str
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
        verified_at=CHECKED,
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
        unknown = set(r.skill_ids) - skills
        if unknown:
            raise ValueError(f"{r.id}: unknown skill ids {sorted(unknown)}")
        if not 1 <= r.level <= 5 or r.hours <= 0 or not r.url.startswith("https://"):
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


def with_verified(row: CourseRow, when: date) -> CourseRow:
    return replace(row, verified_at=when)
