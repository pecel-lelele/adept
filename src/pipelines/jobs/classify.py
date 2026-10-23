"""Turn a raw ad into Adept terms: target role, skills asked, certifications named, seniority.

Pure functions. An opening is linked to an Adept role only when its job title fits one of the
role's title patterns (ordered, most specific first). Matching by skills alone was tried and
dropped: it filed a React developer under ML engineer and an accountant under data analyst.
Unlinked openings still count towards skill demand, and their titles show which jobs the role
catalogue does not cover yet. Skills use the same catalogue matcher as CV parsing, so every
skill id exists in the taxonomy.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# Titles that are never one of Adept's roles, whatever else they mention.
EXCLUDE = re.compile(
    r"counsel|legal|lawyer|attorney|\bdriver\b|\brider\b|interpreter|locali[sz]ation", re.I
)

# Ordered: the first role whose pattern matches the title wins. Domain roles (semiconductor,
# ESG, supply chain, ...) come before the generic data and marketing ones they overlap with.
ROLE_TITLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "responsible-ai-officer",
        (
            r"responsible ai",
            r"ai governance",
            r"ai ethic",
            r"ai risk",
            r"model risk",
        ),
    ),
    (
        "islamic-finance-analyst",
        (
            r"islamic",
            r"shariah",
            r"syariah",
            r"takaful",
            r"sukuk",
        ),
    ),
    (
        "people-analytics-specialist",
        (
            r"people analytic",
            r"hr analyst",
            r"workforce analyst",
            r"hris",
            r"hr data",
            r"talent analytic",
        ),
    ),
    (
        "machine-learning-engineer",
        (
            r"machine learning",
            r"\bml\b",
            r"\bai engineer",
            r"deep learning",
            r"data scientist",
            r"applied scientist",
            r"\bnlp\b",
            r"computer vision",
            r"\bllm",
            r"research scientist",
            r"ai/ml",
        ),
    ),
    (
        "ai-operations-specialist",
        (
            r"\bai (operations|ops|specialist|trainer|tutor|automation)",
            r"\bai coding",
            r"annotat",
            r"genai specialist",
        ),
    ),
    (
        "data-engineer",
        (
            r"data engineer",
            r"\betl\b",
            r"data platform",
            r"big data",
            r"analytics engineer",
            r"data architect",
            r"data warehouse",
        ),
    ),
    (
        "process-automation-analyst",
        (
            r"\brpa\b",
            r"process automation",
            r"automation (analyst|developer|specialist|consultant)",
            r"intelligent automation",
            r"power automate",
            r"uipath",
            r"workflow automation",
            r"power platform",
            r"business process (&|and) automation",
        ),
    ),
    (
        "cybersecurity-analyst",
        (
            r"secur",
            r"\bsoc analyst",
            r"cyber",
            r"penetration",
            r"threat",
            r"incident response",
            r"\bgrc\b",
            r"identity and access",
            r"\biam\b",
            r"red team",
        ),
    ),
    (
        "compliance-analytics-officer",
        (
            r"complian",
            r"\baml\b",
            r"anti-money",
            r"\bkyc\b",
            r"financial crime",
            r"fraud",
            r"sanction",
            r"regulatory report",
            r"risk (operations|control|analyst)",
            r"\bstr\b",
        ),
    ),
    (
        "cloud-solutions-architect",
        (
            r"cloud",
            r"solutions? architect",
            r"devops",
            r"site reliability",
            r"\bsre\b",
            r"platform engineer",
            r"infrastructure (platform |systems )?engineer",
            r"network engineer",
        ),
    ),
    (
        "semiconductor-process-engineer",
        (
            r"semiconductor",
            r"wafer",
            r"\bfab\b",
            r"process integration",
            r"yield",
            r"failure analysis",
            r"packaging",
            r"assembly",
            r"\bate\b",
            r"device engineer",
            r"silicon",
            r"mask layout",
            r"\bsoc\b",
            r"\bcpu\b",
            r"\bgpu\b",
            r"asic",
            r"fpga",
            r"validation engineer",
            r"design engineer",
            r"layout",
            r"product development engineer",
            r"verification engineer",
            r"\bnand\b",
            r"\bnvm\b",
            r"\bdram\b",
            r"test development",
            r"module (equipment )?(engineer|technician)",
            r"characteri[sz]ation",
            r"test floor",
            r"test (equipment )?technician",
            r"equipment technician",
            r"\bosat\b",
            r"\bnpi\b",
            r"reliability",
        ),
    ),
    (
        "smart-manufacturing-engineer",
        (
            r"manufactur",
            r"process engineer",
            r"automation engineer",
            r"industrial engineer",
            r"industry 4\.0",
            r"production (engineer|supervisor)",
            r"equipment engineer",
            r"test engineer",
            r"\bplc\b",
            r"controls engineer",
            r"quality engineer",
            r"mechanical engineer",
            r"electrical engineer",
            r"maintenance engineer",
            r"facilities engineer",
        ),
    ),
    (
        "solar-pv-engineer",
        (
            r"solar",
            r"photovoltaic",
            r"\bpv\b",
            r"renewable",
        ),
    ),
    (
        "energy-manager",
        (r"energy (manager|engineer|efficien|audit)",),
    ),
    (
        "esg-sustainability-analyst",
        (
            r"\besg\b",
            r"sustainab",
            r"climate",
            r"carbon",
            r"decarboni",
        ),
    ),
    (
        "supply-chain-analyst",
        (
            r"supply chain",
            r"demand plan",
            r"supply plan",
            r"material planner",
            r"procurement",
            r"logistics analyst",
            r"inventory",
            r"sourcing",
            r"buyer",
            r"purchas",
            r"category (manager|supplier)",
            r"supplier manager",
            r"transport planner",
            r"control tower",
        ),
    ),
    (
        "precision-agriculture-specialist",
        (
            r"agri",
            r"agronom",
            r"plantation",
            r"precision farm",
        ),
    ),
    (
        "health-informatics-specialist",
        (
            r"health informatic",
            r"clinical data",
            r"healthcare data",
            r"medical informatic",
            r"\behr\b",
        ),
    ),
    (
        "digital-health-nurse",
        (r"\bnurs",),
    ),
    (
        "learning-experience-designer",
        (
            r"instructional design",
            r"learning experience",
            r"learning design",
            r"e-?learning",
            r"curriculum",
            r"learning (and|&) development",
            r"\bl&d\b",
        ),
    ),
    (
        "ai-product-manager",
        (
            r"product manager",
            r"product owner",
            r"product lead",
            r"head of product",
            r"product management",
        ),
    ),
    (
        "ux-designer",
        (
            r"\bux\b",
            r"\bui\b",
            r"user experience",
            r"product designer",
            r"interaction designer",
            r"user research",
        ),
    ),
    (
        "digital-marketing-specialist",
        (
            r"marketing",
            r"\bseo\b",
            r"\bsem\b",
            r"social media",
            r"content (creator|strategist|writer|marketing)",
            r"brand (manager|executive|marketing)",
            r"paid media",
            r"performance media",
            r"copywrit",
        ),
    ),
    (
        "business-analyst",
        (
            r"business analyst",
            r"business systems analyst",
            r"functional (analyst|consultant)",
            r"requirements analyst",
            r"process analyst",
            r"business process",
        ),
    ),
    (
        "data-analyst",
        (
            r"data analy",
            r"analytics",
            r"\bbi\b",
            r"business intelligence",
            r"reporting analyst",
            r"insights? (analyst|intern|manager)",
            r"data scien",
            r"data quality",
            r"data steward",
            r"data governance",
            r"\bmis\b",
        ),
    ),
    (
        "tvet-digital-skills-trainer",
        (
            r"trainer",
            r"training (executive|specialist|manager|coordinator)",
            r"lecturer",
            r"instructor",
        ),
    ),
    (
        "customer-success-specialist",
        (
            r"customer success",
            r"customer support",
            r"customer service",
            r"customer experience",
            r"client success",
            r"customer care",
            r"support (specialist|associate|operations)",
            r"merchant support",
            r"telesales",
            r"client service",
            r"call cent",
        ),
    ),
    (
        "hospitality-experience-manager",
        (
            r"hotel",
            r"hospitality",
            r"guest (relations|experience|service)",
            r"front office",
            r"\bf&b\b",
            r"food (and|&) beverage",
            r"concierge",
            r"housekeeping",
            r"resort",
            r"restaurant",
        ),
    ),
    (
        "bank-operations-executive",
        (
            r"bank operations",
            r"payment operations",
            r"settlement",
            r"reconciliation",
            r"\brecons?\b",
            r"treasury operations",
        ),
    ),
    (
        "logistics-supervisor",
        (
            r"logistics",
            r"warehouse",
            r"hub (supervisor|lead|manager)",
            r"(fleet|dispatch|transport|last mile|station) (supervisor|lead|manager|executive)",
            r"head, last mile",
        ),
    ),
    (
        "data-entry-clerk",
        (r"data entry",),
    ),
)
_ROLE_PATTERNS = tuple((rid, re.compile("|".join(alts), re.I)) for rid, alts in ROLE_TITLES)

# Certifications an ad can name, by exam code or exact credential name (see certifications.py).
CERT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ms-pl-900", r"\bpl-?900\b|power platform fundamentals"),
    ("ms-pl-300", r"\bpl-?300\b|power bi data analyst"),
    ("ms-dp-900", r"\bdp-?900\b|azure data fundamentals"),
    ("ms-dp-700", r"\bdp-?700\b|fabric data engineer"),
    ("ms-az-900", r"\baz-?900\b|azure fundamentals"),
    ("ms-az-104", r"\baz-?104\b|azure administrator"),
    ("ms-ai-901", r"\bai-?90[01]\b|azure ai fundamentals"),
    ("ms-sc-900", r"\bsc-?900\b|security, compliance,? and identity fundamentals"),
    ("ms-sc-200", r"\bsc-?200\b|security operations analyst associate"),
    ("aws-clf-c02", r"\bclf-?c0\d\b|aws certified cloud practitioner|aws cloud practitioner"),
    ("aws-aif-c01", r"\baif-?c0\d\b|aws certified ai practitioner"),
    ("gcp-cdl", r"cloud digital leader"),
    ("iiba-ecba", r"\becba\b"),
    ("iapp-aigp", r"\baigp\b"),
)
_CERT_PATTERNS = tuple((cid, re.compile(rx, re.I)) for cid, rx in CERT_PATTERNS)


def role_from_title(title: str) -> str | None:
    if EXCLUDE.search(title):
        return None
    for rid, rx in _ROLE_PATTERNS:
        if rx.search(title):
            return rid
    return None


@dataclass(frozen=True)
class RoleReq:
    skill_id: str
    importance: float


def assign_role(
    title: str, requirements: Mapping[str, Sequence[RoleReq]]
) -> tuple[str | None, str]:
    """(role_id, 'title') when the title fits a catalogue role, else (None, '')."""
    rid = role_from_title(title)
    return (rid, "title") if rid and rid in requirements else (None, "")


def cert_mentions(text: str) -> list[str]:
    return [cid for cid, rx in _CERT_PATTERNS if rx.search(text)]


_SENIORITY: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "intern",
        re.compile(r"intern|internship|industrial training|placement student|trainee", re.I),
    ),
    (
        "entry",
        re.compile(
            r"graduate|junior|\bjr\b|entry|fresh|associate(?! director)|"
            r"assistant(?! manager)|executive\b|apprentice",
            re.I,
        ),
    ),
    (
        "lead",
        re.compile(
            r"\bhead\b|director|principal|\blead\b|\bvp\b|vice president|chief|staff ", re.I
        ),
    ),
    ("senior", re.compile(r"senior|\bsr\.?\b|manager|specialist ii|expert|consultant", re.I)),
)


def seniority(title: str, level_hint: str = "") -> str:
    hint = level_hint.lower()
    if "intern" in hint:
        return "intern"
    if any(w in hint for w in ("entry", "graduate", "junior")):
        return "entry"
    for label, rx in _SENIORITY:
        if rx.search(title):
            return label
    if any(w in hint for w in ("senior", "director", "executive level", "lead")):
        return "senior"
    return "mid" if hint else "unknown"
