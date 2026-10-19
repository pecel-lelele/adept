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
MSLEARN_SOURCE_URL = "https://learn.microsoft.com/api/learn/catalog"
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

# Paid, HRD Corp-claimable courses checked by hand on the provider's own page or brochure.
MANUAL: tuple[CourseRow, ...] = (
    CourseRow(
        id="aitraining2u-ai-data-analytics",
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
            )
        )
    return rows


def all_rows(
    payload: dict[str, Any], retrieved: date, allow_missing: bool = False
) -> list[CourseRow]:
    return from_mslearn(payload, retrieved, allow_missing) + list(COURSERA) + list(MANUAL)


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
