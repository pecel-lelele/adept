"""CV parsing pipeline (M2-01).

Pipeline stages:
  text input (PDF bytes / raw text)
  → clean_text()            strip noise, normalise whitespace
  → extract_skill_mentions() rule-based keyword scan against taxonomy
  → estimate_level()         heuristic level 1-5 from proficiency signals
  → deduplicate()            highest-confidence result per skill_id

Design constraints (AGENTS.md §3):
  - Never stores uploaded CVs; bytes are processed in-memory only.
  - Never invents skill IDs. Every result must resolve to a taxonomy entry.
  - No real PII; only synthetic CVs are used in demo mode.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Optional: use PyMuPDF (fitz) for PDF text extraction.  Imported lazily so
# the app still boots when the library is absent (text-only mode).
try:
    import fitz  # type: ignore[import-not-found]

    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

_SEED = Path(__file__).resolve().parents[5] / "src" / "data" / "seed"


# ---------------------------------------------------------------------------
# Taxonomy loader
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxonomySkill:
    skill_id: str
    label: str
    # Aliases help the keyword scanner match variants (e.g. "SQL" → "sql")
    aliases: tuple[str, ...]


@lru_cache(maxsize=1)
def _load_taxonomy() -> dict[str, TaxonomySkill]:
    """Load skills.csv and build a {skill_id: TaxonomySkill} dict."""
    path = _SEED / "taxonomy" / "skills.csv"
    taxonomy: dict[str, TaxonomySkill] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["id"]
            label = row["label"]
            # Generate aliases: the label itself, each word, and the id tokens
            alias_set: set[str] = {label.lower(), sid.lower()}
            alias_set.update(w.lower() for w in label.split() if len(w) > 2)
            alias_set.update(sid.replace("-", " ").split())
            taxonomy[sid] = TaxonomySkill(
                skill_id=sid,
                label=label,
                aliases=tuple(sorted(alias_set)),
            )
    return taxonomy


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------


def extract_text_from_pdf(content: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF (fitz).

    Falls back to decoding bytes as UTF-8 text when fitz is unavailable,
    which is sufficient for synthetic text-format CVs used in demo mode.
    """
    if not _HAS_FITZ:
        # Graceful degradation: treat content as raw text.
        return content.decode("utf-8", errors="replace")
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages)
    except Exception:
        return content.decode("utf-8", errors="replace")


def extract_text(filename: str, content: bytes) -> str:
    """Dispatch to the correct extractor based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(content)
    # Plain text / unknown: decode directly.
    return content.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_NOISE_RE = re.compile(
    r"https?://\S+|"  # URLs
    r"\S+@\S+\.\S+|"  # Emails
    r"\b\d{8,}\b|"  # Long number strings (phone numbers etc.)
    r"[^\x20-\x7E\n]",  # Non-printable ASCII
)


def clean_text(raw: str) -> str:
    """Strip PII and formatting noise, normalise whitespace."""
    text = _NOISE_RE.sub(" ", raw)
    # Collapse runs of whitespace/newlines into a single space
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Proficiency signal heuristics
# ---------------------------------------------------------------------------

# Keywords in the CV text that suggest a certain proficiency level (1-5).
_LEVEL_SIGNALS: dict[int, tuple[str, ...]] = {
    5: ("expert", "lead", "principal", "architect", "senior", "advanced", "mastery"),
    4: ("proficient", "experienced", "strong", "solid", "extensive"),
    3: ("intermediate", "working knowledge", "familiar", "confident"),
    2: ("basic", "beginner", "learning", "exposure", "some experience"),
    1: ("awareness", "interested", "studied"),
}

# Pre-compile a pattern for each level
_LEVEL_PATTERNS: dict[int, re.Pattern[str]] = {
    lvl: re.compile("|".join(re.escape(kw) for kw in kws), re.IGNORECASE)
    for lvl, kws in _LEVEL_SIGNALS.items()
}


def _estimate_level_from_context(surrounding: str) -> int:
    """Return the highest-priority level found in the surrounding text window.

    Scans the text within ~50 characters of a skill mention.
    Defaults to 2 (beginner) if no signal is found.
    """
    for lvl in (5, 4, 3, 2, 1):
        if _LEVEL_PATTERNS[lvl].search(surrounding):
            return lvl
    return 2  # default: beginner


# ---------------------------------------------------------------------------
# Confidence score
# ---------------------------------------------------------------------------


def _confidence(num_occurrences: int, context_match: bool) -> float:
    """Heuristic confidence between 0 and 1.

    Factors:
      - At least one mention: base 0.50
      - Multiple mentions: +0.15 each, capped at 0.80
      - Context (proficiency keyword nearby): +0.15
    """
    score = min(0.50 + 0.15 * (num_occurrences - 1), 0.80)
    if context_match:
        score = min(score + 0.15, 0.95)
    return round(score, 2)


# ---------------------------------------------------------------------------
# Extracted result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedSkill:
    skill_id: str
    label: str
    level: int  # 1-5 scale (maps to 0.0-1.0 in matching engine)
    confidence: float  # 0.0-1.0


# ---------------------------------------------------------------------------
# Core extraction pipeline
# ---------------------------------------------------------------------------


def _build_alias_index(
    taxonomy: dict[str, TaxonomySkill],
) -> list[tuple[re.Pattern[str], str]]:
    """Build a list of (compiled_pattern, skill_id) sorted longest-alias-first.

    Longest-first ensures "machine learning" matches before "machine".
    """
    entries: list[tuple[str, str]] = []
    for skill in taxonomy.values():
        for alias in skill.aliases:
            entries.append((alias, skill.skill_id))
    # Sort by alias length descending to prefer longer (more specific) matches
    entries.sort(key=lambda t: len(t[0]), reverse=True)
    return [
        (re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE), sid) for alias, sid in entries
    ]


@lru_cache(maxsize=1)
def _alias_index() -> list[tuple[re.Pattern[str], str]]:
    return _build_alias_index(_load_taxonomy())


def extract_skills(text: str) -> list[ParsedSkill]:
    """Scan cleaned CV text and return matched skills sorted by confidence desc.

    Each skill_id appears at most once (highest-confidence occurrence wins).
    """
    taxonomy = _load_taxonomy()
    index = _alias_index()

    # Accumulate: {skill_id: (occurrences, max_level, any_context_match)}
    hits: dict[str, list[int | bool]] = {}  # [count, level, context_found]

    for pattern, sid in index:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]
            level = _estimate_level_from_context(context)
            has_context = any(_LEVEL_PATTERNS[lvl].search(context) for lvl in _LEVEL_PATTERNS)

            if sid not in hits:
                hits[sid] = [1, level, has_context]
            else:
                hits[sid][0] += 1
                if level > hits[sid][1]:
                    hits[sid][1] = level
                if has_context:
                    hits[sid][2] = True

    results: list[ParsedSkill] = []
    for sid, (count, level, ctx) in hits.items():
        results.append(
            ParsedSkill(
                skill_id=sid,
                label=taxonomy[sid].label,
                level=int(level),
                confidence=_confidence(int(count), bool(ctx)),
            )
        )

    # Sort: highest confidence first, then alphabetically for determinism
    results.sort(key=lambda s: (-s.confidence, s.skill_id))
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_cv(filename: str, content: bytes) -> list[ParsedSkill]:
    """Full pipeline: extract text → clean → scan for skills.

    Args:
        filename: Original filename; used to determine extraction strategy.
        content:  Raw file bytes.  Never persisted.

    Returns:
        List of ParsedSkill ordered by confidence (highest first).
        Empty list if the content yields no text or no taxonomy matches.
    """
    raw_text = extract_text(filename, content)
    cleaned = clean_text(raw_text)
    return extract_skills(cleaned)
