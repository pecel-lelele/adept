"""Counterfactual fairness check for CV parsing and role matching (F4/F8).

Two checks, both calling production code only (nothing is patched, copied or saved):

1. **Input exclusion by introspection.** The scoring input (`MatchProfile`) and the saved
   `Profile` fields it is built from contain no protected attribute (`app.core.fairness`).
   `Profile` has no age, gender or background field at all, so swapping such fields on a
   Profile could never change a result; that is why this harness varies CV *text* instead.
2. **CV-text counterfactuals.** For each synthetic demo CV in `docs/demo-cvs/`, the text is
   extracted with the public bounded PDF parser, then rewritten into variants that swap the
   name (to another demo CV's synthetic name), add gendered titles, pronouns and gendered
   wording, and state different ages. Every variant runs through the production CV
   extraction (`extract_cv`) and the production ranking (`rank_roles` over `load_roles()`
   and the trend snapshot from `fetch_snapshot`), the same path as the guest preview. Each
   variant must yield the same extracted skills and levels (what the person then confirms)
   and the same role ranking and scores as the unchanged CV.

    source        → the five synthetic demo CV PDFs (fictional people, example.test emails)
    preprocessing → `extract_pdf_bounded` text; deterministic identity rewrites only
    features      → `extract_cv` skill IDs and levels (suggestions off: no embedding calls)
    model/method  → `rank_roles(MatchProfile(skills), load_roles(), snapshot velocities)`
    evaluation    → exact equality of skills and of (role_id, score) rankings per variant
    serving       → CLI JSON log: file names, variant labels, outcomes; never CV text

Run from the repository root (reads the configured trend snapshot; writes nothing else):
    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.guardrails.matching_counterfactual \
        --out generated-artifacts/fairness/matching_counterfactual.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.contracts.common import ScenarioId
from app.contracts.profile import Profile
from app.core.fairness import protected_terms_in
from app.features.matching.repository import load_roles
from app.features.matching.scoring import MatchProfile, rank_roles
from app.features.matching.trend_port import fetch_snapshot
from app.features.profile.cv_parser import extract_pdf_bounded
from app.features.profile.service import extract_cv

ROOT = Path(__file__).resolve().parents[3]
DEMO_CVS = ROOT / "docs" / "demo-cvs"

# Saved-profile fields the matching repository reads to build MatchProfile (M2-12 whitelist).
PROFILE_FIELDS_USED_BY_MATCHING = ("skills", "interests")


def scoring_input_fields() -> dict[str, list[str]]:
    """Field names that feed role scoring, read from the production types themselves."""
    return {
        "MatchProfile": [f.name for f in dataclasses.fields(MatchProfile)],
        "Profile": sorted(Profile.model_fields),
        "Profile (used by matching)": list(PROFILE_FIELDS_USED_BY_MATCHING),
    }


def check_scoring_inputs() -> None:
    """Raise if any scoring input or profile field names a protected attribute."""
    fields = scoring_input_fields()
    missing = set(PROFILE_FIELDS_USED_BY_MATCHING) - set(fields["Profile"])
    if missing:
        raise AssertionError(f"Matching reads profile fields that no longer exist: {missing}")
    if set(fields["MatchProfile"]) != set(PROFILE_FIELDS_USED_BY_MATCHING):
        raise AssertionError("MatchProfile fields changed; review the fairness whitelist")
    flagged = {name: protected_terms_in(names) for name, names in fields.items()}
    flagged = {name: terms for name, terms in flagged.items() if terms}
    if flagged:
        raise AssertionError(f"Protected attributes reach scoring inputs: {flagged}")


# --- CV-text variants --------------------------------------------------------------------

# Identity statements added to a CV. Values are paired so each attribute is varied while the
# rest of the CV stays fixed. No real person is described: the names come from the demo CVs.
IDENTITY_LINES: dict[str, str] = {
    "pronouns-she": "Pronouns: she/her. She is open to hybrid work.",
    "pronouns-he": "Pronouns: he/him. He is open to hybrid work.",
    "pronouns-they": "Pronouns: they/them. They are open to hybrid work.",
    "gender-female": "Gender: female. Former chairwoman of the staff wellbeing committee.",
    "gender-male": "Gender: male. Former chairman of the staff wellbeing committee.",
    "age-24": "Age: 24 (date of birth 2002).",
    "age-41": "Age: 41 (date of birth 1985).",
    "age-58": "Age: 58 (date of birth 1968). Aged 58 years old.",
}


def cv_name(text: str) -> str:
    """The CV's own name: its first non-empty line (the demo CVs print it as a heading)."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    raise ValueError("CV text has no heading line")


def _swap_name(text: str, name: str, other: str) -> str:
    """Replace a name in heading, title-case and e-mail forms with another synthetic name."""
    forms = [
        (name.upper(), other.upper()),
        (name.title(), other.title()),
        (name.lower().replace(" ", "."), other.lower().replace(" ", ".")),
    ]
    for old, new in forms:
        text = re.sub(re.escape(old), new, text)
    return text


def _with_line(text: str, line: str) -> str:
    """Add an identity statement under the CV's heading (where personal details usually go)."""
    head, _, rest = text.partition("\n")
    return f"{head}\n{line}\n{rest}"


def cv_variants(text: str, other_name: str) -> dict[str, str]:
    """Labelled counterfactual rewrites of one CV's text (the baseline is the CV itself)."""
    name = cv_name(text)
    variants = {
        "baseline": text,
        f"name-swap:{other_name.title()}": _swap_name(text, name, other_name),
    }
    variants["title-ms"] = text.replace(name, f"MS {name}", 1)
    variants["title-mr"] = text.replace(name, f"MR {name}", 1)
    for label, line in IDENTITY_LINES.items():
        variants[label] = _with_line(text, line)
    variants["combined:name+she+age-58"] = _with_line(
        _swap_name(text, name, other_name),
        " ".join([IDENTITY_LINES["pronouns-she"], IDENTITY_LINES["age-58"]]),
    )
    return variants


# --- production parsing + matching ---------------------------------------------------------


Outcome = dict[str, Any]
CvReader = Callable[[Path], str]


def match_cv_text(text: str, scenario: ScenarioId, velocities: dict[str, float]) -> Outcome:
    """Skills and the full role ranking for one CV text, via the production functions."""
    extraction = extract_cv("cv.txt", text.encode("utf-8"), "text/plain", include_suggestions=False)
    skills = sorted((s.skill_id, s.level) for s in extraction.skills)
    ranked = rank_roles(MatchProfile(skills=dict(skills)), load_roles(), velocities)
    return {
        "skills": [list(s) for s in skills],
        "ranking": [[r.role_id, round(r.score, 6)] for r in ranked],
    }


def read_pdf(path: Path) -> str:
    return extract_pdf_bounded(path.read_bytes())


def run_cv_counterfactuals(
    paths: Iterable[Path] | None = None,
    scenario: ScenarioId = "moderate",
    read: CvReader = read_pdf,
) -> dict[str, Any]:
    """Run every variant of every CV and return a log (file names and labels, no CV text)."""
    cvs = sorted(paths) if paths is not None else sorted(DEMO_CVS.glob("*.pdf"))
    if len(cvs) < 2:
        raise ValueError("Name swaps need at least two synthetic CVs")
    snapshot = fetch_snapshot(scenario)
    texts = {path.name: read(path) for path in cvs}
    names = [cv_name(text) for text in texts.values()]
    results: list[dict[str, Any]] = []
    for index, (file_name, text) in enumerate(texts.items()):
        other = names[(index + 1) % len(names)]
        expected: Outcome | None = None
        for label, variant in cv_variants(text, other).items():
            outcome = match_cv_text(variant, scenario, snapshot.velocities)
            if expected is None:
                expected = outcome
                if not outcome["skills"] or not outcome["ranking"]:
                    raise AssertionError(f"{file_name}: no skills or roles; the check is vacuous")
            results.append(
                {
                    "file": file_name,
                    "variant": label,
                    "skills": len(outcome["skills"]),
                    "top_role": outcome["ranking"][0][0] if outcome["ranking"] else None,
                    "same_skills": outcome["skills"] == expected["skills"],
                    "same_ranking": outcome["ranking"] == expected["ranking"],
                }
            )
    return {
        "check": "matching_counterfactual",
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scenario": scenario,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "snapshot_is_fallback": bool(getattr(snapshot, "is_fallback", False)),
        "scoring_inputs": scoring_input_fields(),
        "cases": results,
        "invariant": all(r["same_skills"] and r["same_ranking"] for r in results),
    }


def check_matching_counterfactual(
    paths: Iterable[Path] | None = None,
    scenario: ScenarioId = "moderate",
    read: CvReader = read_pdf,
) -> dict[str, Any]:
    """Both checks; raises AssertionError naming every variant that changed a result."""
    check_scoring_inputs()
    report = run_cv_counterfactuals(paths, scenario, read)
    changed = [
        f"{r['file']}:{r['variant']}"
        for r in report["cases"]
        if not (r["same_skills"] and r["same_ranking"])
    ]
    if changed:
        raise AssertionError(f"Identity-only CV changes altered skills or ranks: {changed}")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="JSON log path to write")
    ap.add_argument("--scenario", choices=["moderate", "fast"], default="moderate")
    args = ap.parse_args(argv)
    check_scoring_inputs()
    report = run_cv_counterfactuals(scenario=args.scenario)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{len(report['cases'])} cases, invariant={report['invariant']} -> {args.out}")
    return 0 if report["invariant"] else 1


if __name__ == "__main__":
    sys.exit(main())
