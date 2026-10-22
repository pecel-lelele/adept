"""CV parsing pipeline (M2-01) — Prompt 5 rewrite.

Pipeline stages:
  raw bytes  (content_type validated by router)
  → extract_text()             PDF via PyMuPDF only (page cap, encrypted files refused);
                               DOCX via the standard library (zip-bomb guarded); text as
                               UTF-8. Binary bytes are never decoded as text.
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
import io
import math
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from itertools import islice
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

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

#: Pages read from a PDF. A CV is rarely longer than a few pages; the cap bounds the work a
#: hostile or accidental 500-page upload can cause.
MAX_PDF_PAGES = 30

#: DOCX limits: a .docx is a zip, so its XML size is checked before it is decompressed.
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024
MAX_DOCX_ENTRIES = 2_000

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_SEED = Path(__file__).resolve().parents[5] / "src" / "data" / "seed"

#: Chinese, Japanese and Korean characters (written without spaces between words).
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")

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
            pattern=_phrase_pattern(phrase),
            skill_id=sid,
            phrase_len=len(phrase),
            phrase=phrase.lower(),
        )
        for phrase, sid in entries
    ]


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Whole-word match for Latin-script phrases. Chinese and Japanese are written without
    spaces, so a word boundary would never match inside a sentence; CJK phrases match as
    plain substrings instead."""
    if _CJK_RE.search(phrase):
        return re.compile(re.escape(phrase))
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)


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
    if mime == DOCX_MIME:
        return _extract_docx(raw_bytes)
    if raw_bytes[:4] in (b"%PDF", b"PK\x03\x04"):
        # A PDF or Word file sent as text/plain (wrong extension): never scan bytes as text.
        raise AppError(
            "This file looks like a PDF or Word document saved with the wrong type. "
            "Upload it as .pdf or .docx.",
            status_code=422,
            code="wrong_file_type",
        )
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

    unreadable = AppError(
        "Could not read the uploaded PDF. It may be corrupted or not a PDF at all.",
        status_code=422,
        code="pdf_unreadable",
    )
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise unreadable
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise unreadable from exc
    try:
        if doc.needs_pass:
            raise AppError(
                "This PDF is password-protected. Save a copy without a password and try again.",
                status_code=422,
                code="pdf_encrypted",
            )
        pages = [str(page.get_text()) for page in islice(doc, MAX_PDF_PAGES)]
    except AppError:
        raise
    except Exception as exc:
        raise unreadable from exc
    finally:
        doc.close()

    text = "\n".join(pages)
    if not text.strip():
        raise PdfNoText()

    return text


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DOCX_PART = re.compile(r"word/(document|header\d*|footer\d*)\.xml")


def _extract_docx(data: bytes) -> str:
    """Text of a Word (.docx) CV: paragraphs and table cells, then headers and footers.

    Standard library only. The archive is checked before anything is decompressed: too many
    entries, or XML parts that would inflate past MAX_DOCX_XML_BYTES, are refused, so a zip bomb
    cannot exhaust memory. OOXML parts carry no DTD, and ElementTree does not fetch entities.
    """
    unreadable = AppError(
        "Could not read the Word document. Save it again as .docx or upload a PDF.",
        status_code=422,
        code="docx_unreadable",
    )
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError) as exc:
        raise unreadable from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_DOCX_ENTRIES:
            raise unreadable
        parts = sorted(
            (i for i in infos if _DOCX_PART.fullmatch(i.filename)),
            key=lambda i: i.filename != "word/document.xml",
        )
        if not parts or parts[0].filename != "word/document.xml":
            raise unreadable
        if sum(i.file_size for i in parts) > MAX_DOCX_XML_BYTES:
            raise AppError(
                "This Word document is too large to read as a CV.",
                status_code=413,
                code="payload_too_large",
            )
        chunks: list[str] = []
        for info in parts:
            try:
                with archive.open(info) as fh:
                    root = ElementTree.fromstring(fh.read(MAX_DOCX_XML_BYTES + 1))  # noqa: S314
            except (zipfile.BadZipFile, ElementTree.ParseError, RuntimeError, OSError) as exc:
                raise unreadable from exc
            for para in root.iter(f"{_W_NS}p"):
                line = "".join(t.text or "" for t in para.iter(f"{_W_NS}t"))
                if line.strip():
                    chunks.append(line)
    text = "\n".join(chunks)
    if not text.strip():
        raise AppError(
            "We found no text in this Word document. You can pick your skills on the next step.",
            status_code=422,
            code="docx_no_text",
        )
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
    5: ("expert", "principal", "architect", "mastery", "pakar", "专家", "精通"),
    4: ("advanced", "proficient", "experienced", "extensive", "strong", "mahir", "熟练"),
    3: ("intermediate", "working knowledge", "familiar", "confident", "sederhana", "熟悉"),
    2: ("basic", "beginner", "some experience", "exposure to", "asas", "了解"),
    1: ("awareness", "interested in", "currently learning", "berminat", "学习中"),
}


def _signal_pattern(words: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(
        "|".join(_phrase_pattern(w).pattern for w in words),
        re.IGNORECASE,
    )


# Whole words only: "lead" no longer fires inside "leadership", nor "learning" inside
# "machine learning"; job-title words ("senior", "lead") are not skill-level cues.
_LEVEL_PATTERNS: dict[int, re.Pattern[str]] = {
    lvl: _signal_pattern(kws) for lvl, kws in _LEVEL_SIGNALS.items()
}

#: "5 years", "3+ yrs", "2 tahun" (Malay) or "3年" (Chinese) next to a skill.
_YEARS_RE = re.compile(r"(\d{1,2})(?:\.\d)?\s*\+?\s*(?:years?|yrs?|tahun|年)", re.IGNORECASE)

#: A skill named just after one of these is one the person says they do not have.
_NEGATION_RE = re.compile(
    r"(?:\bno\b|\bwithout\b|\bnot familiar with\b|\black(?:ing)? of\b|"
    r"\btiada pengalaman\b|\btidak mahir\b|没有|不熟悉)[^.;,\n]{0,25}$",
    re.IGNORECASE,
)

#: Characters either side of a mention read for level cues. Narrow on purpose: a wider window
#: picked up "Senior Manager" from a nearby job title.
_CONTEXT_CHARS = 45


def _level_from_years(years: int) -> int:
    if years >= 8:
        return 5
    if years >= 5:
        return 4
    if years >= 3:
        return 3
    return 2


def _estimate_level(context: str) -> int:
    """Highest level cue in the context, else years of experience, else 2 (beginner)."""
    for lvl in (5, 4, 3, 2, 1):
        if _LEVEL_PATTERNS[lvl].search(context):
            return lvl
    years = _YEARS_RE.search(context)
    if years:
        return _level_from_years(int(years.group(1)))
    return 2


def _is_negated(text: str, start: int) -> bool:
    """True when the words just before a mention deny it ("no experience in SQL")."""
    return bool(_NEGATION_RE.search(text[max(0, start - 40) : start]))


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
            if _is_negated(normed, s):
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
        ctx_start = max(0, first_s - _CONTEXT_CHARS)
        ctx_end = min(len(text), first_e + _CONTEXT_CHARS)
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
