"""F5 pipeline (owner M3): course catalogue → src/data/seed/courses/courses.csv.

The pathway may only recommend courses in this file ("catalogue-only" rule). Two inputs:

1. **Microsoft Learn Catalog API** (`GET https://learn.microsoft.com/api/learn/catalog`,
   public, no key). We keep a curated list of module / learning-path UIDs mapped to our skill
   IDs; title, URL and duration come from the API at fetch time, so they stay current.
   Microsoft Learn is free (cost RM 0, nothing to claim from HRD Corp).
2. **Manually verified provider pages** (`MANUAL`): paid, HRD Corp-claimable courses whose
   claimability and fee are stated on the provider's own page, with the date we checked.

    source        → API response + MANUAL rows
    preprocessing → strip tracking params from URLs; minutes → hours (1 decimal)
    validation    → every curated UID must exist in the API response; skill IDs must exist in
                    the taxonomy; level 1-5; hours > 0
    serving       → courses.csv (DB via `make seed`; read directly by the API in mock mode)

`level` is the skill level (1-5) Adept estimates a learner reaches after the course. It is an
Adept judgment, shown to users as an estimate.

Run from the repo root:  PYTHONPATH=src .venv/bin/python -m pipelines.pathway.run
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

API_URL = "https://learn.microsoft.com/api/learn/catalog?locale=en-us&type=modules,learningPaths"
SEED = Path(__file__).resolve().parents[2] / "data" / "seed"
OUT = SEED / "courses" / "courses.csv"
MS_SOURCE = "Microsoft Learn Catalog API"
MS_SOURCE_URL = "https://learn.microsoft.com/api/learn/catalog"


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
    Curated("mslearn-python-2", "learn.wwl.get-started-with-python-programs", ("python",), 3),
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


# Checked by hand on the provider's own page on `verified_at`.
MANUAL: tuple[CourseRow, ...] = (
    CourseRow(
        id="aitraining2u-ai-data-analytics",
        title="AI Data Analytics Training (2 days)",
        provider="AITraining2U",
        url="https://www.aitraining2u.com/aianalytics.html",
        hours=14,
        cost_myr=3500,
        hrd_claimable=True,
        verified_at=date(2026, 10, 20),
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
)


def clean_url(url: str) -> str:
    """Drop query and fragment (the API adds a tracking parameter)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def from_catalog(payload: dict[str, Any], retrieved: date) -> list[CourseRow]:
    index = {i["uid"]: i for key in ("modules", "learningPaths") for i in payload.get(key, [])}
    missing = [c.uid for c in CURATED if c.uid not in index]
    if missing:
        raise ValueError(f"curated UIDs not in the catalogue (retired?): {missing}")
    rows: list[CourseRow] = []
    for c in CURATED:
        item = index[c.uid]
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
                source_name=MS_SOURCE,
                source_url=MS_SOURCE_URL,
                hrd_note="Free; nothing to claim.",
                duration_note=f"Microsoft Learn {kind}, {minutes} min as listed by the provider.",
            )
        )
    return rows


def known_skills(seed: Path = SEED) -> set[str]:
    with (seed / "taxonomy" / "skills.csv").open(encoding="utf-8") as fh:
        return {row["id"] for row in csv.DictReader(fh)}


def validate(rows: list[CourseRow], skills: set[str]) -> None:
    ids = [r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate course ids")
    for r in rows:
        unknown = set(r.skill_ids) - skills
        if unknown:
            raise ValueError(f"{r.id}: unknown skill ids {sorted(unknown)}")
        if not 1 <= r.level <= 5 or r.hours <= 0 or not r.url.startswith("https://"):
            raise ValueError(f"{r.id}: invalid level, hours or url")


def write(rows: list[CourseRow], out: Path = OUT) -> None:
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


def fetch(url: str = API_URL, timeout_s: int = 120) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_s, context=ssl.create_default_context()) as r:
        data: dict[str, Any] = json.load(r)
    return data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--retrieved", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    payload = json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file else fetch()
    rows = from_catalog(payload, args.retrieved) + list(MANUAL)
    validate(rows, known_skills())
    write(rows, args.out)
    print(f"pipelines.pathway: {len(rows)} courses -> {args.out}")


if __name__ == "__main__":
    main()
