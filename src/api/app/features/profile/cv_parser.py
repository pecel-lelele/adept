"""CV parsing pipeline (M2-01) — Prompt 5 rewrite.

Pipeline stages:
  raw bytes  (content_type validated by router)
  → extract_text()             PDF via PyMuPDF only; text via UTF-8. PDF bytes are
                               never decoded as text — unreadable PDFs raise.
  → _truncate_text()           cap at MAX_TEXT_CHARS, set truncated flag
  → _clean_text()              NFKC, ReDoS-safe PII removal, whitespace collapse
  → extract_skills()           taxonomy-only, longest-alias-first, non-overlapping spans
  → sorted by confidence desc

Design constraints (AGENTS.md §3):
  - Never stores uploaded CVs; bytes are processed in-memory only.
  - Never invents skill IDs. Every result must resolve to a taxonomy entry.
  - No real PII; only synthetic CVs are used in demo mode.
  - All regexes are bounded to prevent ReDoS.

Announce to team (package dependency):
  PDF support needs PyMuPDF, now declared in requirements.txt as
    pymupdf>=1.24.0,<2
  The PyPI package installs the ``pymupdf`` module (``fitz`` is its older alias);
  both import names are accepted above. 2.x is excluded because it deprecates
  ``fitz`` and pulls four extra packages into every ``make setup``.
"""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.errors import AppError, PdfNoText, PdfSupportUnavailable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum characters of extracted text to scan. Content beyond this is dropped
#: and the caller receives ``truncated=True``.
MAX_TEXT_CHARS = 200_000

#: Confidence increment per non-overlapping match, capped at 1.0.
#: confidence = min(match_count * CONFIDENCE_PER_HIT, 1.0)
CONFIDENCE_PER_HIT = 0.30
MAX_CONFIDENCE_HITS = math.ceil(1.0 / CONFIDENCE_PER_HIT)

_SEED = Path(__file__).resolve().parents[5] / "src" / "data" / "seed"

# ---------------------------------------------------------------------------
# Optional PyMuPDF import — must NOT fall back silently to decoding PDF bytes
# ---------------------------------------------------------------------------

fitz: Any = None
try:
    import pymupdf as fitz  # type: ignore[import-not-found]

    _HAS_FITZ = True
except ImportError:
    try:
        import fitz  # type: ignore[no-redef,import-not-found]

        _HAS_FITZ = True
    except ImportError:
        _HAS_FITZ = False

# ---------------------------------------------------------------------------
# Safe, bounded PII-removal patterns (ReDoS-safe — all quantifiers are bounded)
# ---------------------------------------------------------------------------

#: Email pattern: local part <=64 chars, domain <=255 chars, both non-whitespace.
_EMAIL_RE = re.compile(r"[^\s@]{1,64}@[^\s@]{1,255}")

#: URLs: http/https scheme only, bounded to 2048 chars.
_URL_RE = re.compile(r"https?://\S{1,2048}")

#: Phone-like strings: 8+ consecutive digits (bounded at 20).
_PHONE_RE = re.compile(r"\b\d{8,20}\b")

# ---------------------------------------------------------------------------
# Taxonomy loader
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxonomySkill:
    skill_id: str
    label: str
    #: NFKC-normalised, lowercased label used for matching.
    normalised_label: str
    #: Explicit aliases loaded from taxonomy seed table (Prompt 5 rule 5).
    aliases: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _load_taxonomy() -> dict[str, TaxonomySkill]:
    """Load skills.csv and build a {skill_id: TaxonomySkill} dict."""
    path = _SEED / "taxonomy" / "skills.csv"
    taxonomy: dict[str, TaxonomySkill] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["id"]
            label = row["label"]
            norm = unicodedata.normalize("NFKC", label).lower()
            raw_aliases = row.get("aliases") or ""
            aliases = tuple(
                unicodedata.normalize("NFKC", a.strip()).lower()
                for a in raw_aliases.split("|")
                if a.strip()
            )
            taxonomy[sid] = TaxonomySkill(
                skill_id=sid,
                label=label,
                normalised_label=norm,
                aliases=aliases,
            )
    return taxonomy


# ---------------------------------------------------------------------------
# Alias index — longest-alias-first, word-boundary patterns
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AliasEntry:
    pattern: re.Pattern[str]
    skill_id: str
    phrase_len: int
    phrase: str = ""


@lru_cache(maxsize=1)
def _build_alias_index() -> list[_AliasEntry]:
    """Build alias entries sorted longest-phrase-first.

    Uses ``(?<!\\w)phrase(?!\\w)`` boundaries to avoid sub-word matches
    (e.g. "java" must not match inside "javascript").
    """
    taxonomy = _load_taxonomy()
    seen: set[tuple[str, str]] = set()
    entries: list[tuple[str, str]] = []

    for skill in taxonomy.values():
        if (skill.normalised_label, skill.skill_id) not in seen:
            seen.add((skill.normalised_label, skill.skill_id))
            entries.append((skill.normalised_label, skill.skill_id))
        for alias in skill.aliases:
            if (alias, skill.skill_id) not in seen:
                seen.add((alias, skill.skill_id))
                entries.append((alias, skill.skill_id))

    # Sort: longest phrase first so "python programming" wins over "python"
    entries.sort(key=lambda t: len(t[0]), reverse=True)

    return [
        _AliasEntry(
            pattern=re.compile(
                r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                re.IGNORECASE,
            ),
            skill_id=sid,
            phrase_len=len(phrase),
            phrase=phrase.lower(),
        )
        for phrase, sid in entries
    ]


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text(data: bytes | str, content_type: str = "text/plain") -> str:
    """Extract plain text from uploaded bytes.

    PDF bytes are read *only* through PyMuPDF. They are never decoded as text:
    a binary blob fed into the skill scanner is garbage in, garbage out, and an
    unreadable file must surface as an error instead.

    Args:
        data:         Raw file bytes (a str is treated as the text itself).
        content_type: MIME type as declared by the client.

    Returns:
        Extracted plain text string (may be empty for blank documents).

    Raises:
        PdfSupportUnavailable: fitz (PyMuPDF) is not installed.
        AppError (422):        the PDF is empty or cannot be opened.
        PdfNoText:             the PDF has no extractable text (scanned image).
    """
    raw_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
    mime = content_type.lower().split(";")[0].strip()
    if "pdf" in mime:
        return _extract_pdf(raw_bytes)
    return raw_bytes.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF.

    Raises:
        PdfSupportUnavailable: fitz is absent (501) — a server capability problem.
        AppError (422):        the file is empty or is not a readable PDF — a user
                               input problem, so it must not masquerade as 501.
        PdfNoText:             the PDF yields no text on any page (422).
    """
    if not _HAS_FITZ or fitz is None:
        raise PdfSupportUnavailable()

    if not data:
        raise AppError(
            "The uploaded PDF is empty. Attach the CV file itself, not a link.",
            status_code=422,
            code="pdf_unreadable",
        )

    try:
        doc = fitz.open(stream=data, filetype="pdf")
        pages = [str(page.get_text()) for page in doc]
        doc.close()
    except Exception as exc:
        raise AppError(
            "Could not read the uploaded PDF. It may be corrupted or not a PDF at all.",
            status_code=422,
            code="pdf_unreadable",
        ) from exc

    text = "\n".join(pages)
    if not text.strip():
        raise PdfNoText()

    return text


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------


def _truncate_text(text: str) -> tuple[str, bool]:
    """Return (text[:MAX_TEXT_CHARS], truncated_flag)."""
    if len(text) <= MAX_TEXT_CHARS:
        return text, False
    return text[:MAX_TEXT_CHARS], True


def _clean_text(raw: str) -> str:
    """Apply NFKC normalisation, strip PII, collapse whitespace.

    All removal patterns are bounded and pre-compiled to prevent ReDoS.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _PHONE_RE.sub(" ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


clean_text = _clean_text


# ---------------------------------------------------------------------------
# Extracted result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedSkill:
    skill_id: str
    label: str
    level: int  # 1-5 scale
    confidence: float  # 0.0-1.0


# ---------------------------------------------------------------------------
# Proficiency heuristic
# ---------------------------------------------------------------------------

_LEVEL_SIGNALS: dict[int, tuple[str, ...]] = {
    5: ("expert", "lead", "principal", "architect", "senior", "advanced", "mastery"),
    4: ("proficient", "experienced", "strong", "solid", "extensive"),
    3: ("intermediate", "working knowledge", "familiar", "confident"),
    2: ("basic", "beginner", "learning", "exposure", "some experience"),
    1: ("awareness", "interested", "studied"),
}

_LEVEL_PATTERNS: dict[int, re.Pattern[str]] = {
    lvl: re.compile("|".join(re.escape(kw) for kw in kws), re.IGNORECASE)
    for lvl, kws in _LEVEL_SIGNALS.items()
}


def _estimate_level(context: str) -> int:
    """Return highest-priority level found in the surrounding context text."""
    for lvl in (5, 4, 3, 2, 1):
        if _LEVEL_PATTERNS[lvl].search(context):
            return lvl
    return 2  # default: beginner


# ---------------------------------------------------------------------------
# Core skill extraction
# ---------------------------------------------------------------------------


def extract_skills(text: str) -> list[ParsedSkill]:
    """Scan cleaned CV text; return only catalogue-registered skills.

    Algorithm:
      - NFKC + lowercase the text once for matching.
      - Walk alias entries longest-first.
      - Track matched (start, end) spans per skill; skip overlapping hits.
      - confidence = min(non_overlapping_count * CONFIDENCE_PER_HIT, 1.0).
      - Estimate level from context window around the first hit.

    Returns:
        Skills sorted by confidence desc, skill_id asc.
        Every skill_id is guaranteed to exist in the taxonomy.
    """
    taxonomy = _load_taxonomy()
    index = _build_alias_index()

    normed = unicodedata.normalize("NFKC", text).lower()

    # {skill_id: list of non-overlapping (start, end) spans}
    spans: dict[str, list[tuple[int, int]]] = {}

    for entry in index:
        sid = entry.skill_id
        existing = spans.get(sid, [])
        if len(existing) >= MAX_CONFIDENCE_HITS:
            continue
        # Cheap substring check first: most of the 110+ skills are absent from any one CV,
        # and a regex scan per absent alias dominated parsing time on long texts.
        if entry.phrase and entry.phrase not in normed:
            continue
        for m in entry.pattern.finditer(normed):
            if len(existing) >= MAX_CONFIDENCE_HITS:
                break
            s, e = m.start(), m.end()

            # Skip if this match overlaps any already-recorded span for this skill
            if any(s < ex_e and e > ex_s for ex_s, ex_e in existing):
                continue
            if sid not in spans:
                spans[sid] = existing
            existing.append((s, e))

    if not spans:
        return []

    results: list[ParsedSkill] = []
    for sid, hit_spans in spans.items():
        count = len(hit_spans)
        confidence = min(count * CONFIDENCE_PER_HIT, 1.0)
        # Level from context around the first hit (using original-case text)
        first_s, first_e = hit_spans[0]
        ctx_start = max(0, first_s - 60)
        ctx_end = min(len(text), first_e + 60)
        context = text[ctx_start:ctx_end]
        level = _estimate_level(context)

        results.append(
            ParsedSkill(
                skill_id=sid,
                label=taxonomy[sid].label,
                level=level,
                confidence=round(confidence, 2),
            )
        )

    results.sort(key=lambda s: (-s.confidence, s.skill_id))
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_cv(data: bytes | str, content_type: str = "text/plain") -> tuple[list[ParsedSkill], bool]:
    """Full pipeline: extract text -> truncate -> clean -> scan skills.

    Args:
        data:         Raw file bytes (never persisted) or the text itself.
        content_type: MIME type string from the HTTP request.

    Returns:
        (parsed_skills, truncated) — every skill_id is guaranteed to exist in
        the taxonomy, and `truncated` reports whether text past MAX_TEXT_CHARS
        was dropped before scanning.

    Raises:
        PdfSupportUnavailable: fitz absent and a PDF was uploaded.
        AppError (422):        empty or unreadable PDF.
        PdfNoText:             PDF has no extractable text.
    """
    raw_text = extract_text(data, content_type)
    truncated_text, truncated = _truncate_text(raw_text)
    cleaned = _clean_text(truncated_text)
    return extract_skills(cleaned), truncated
