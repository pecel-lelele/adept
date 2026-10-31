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

import io
import math
import multiprocessing
import os
import re
import threading
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from itertools import islice
from multiprocessing.connection import Connection
from typing import Any
from xml.etree import ElementTree

from app.core import refdata
from app.core import taxonomy as skill_taxonomy
from app.core.errors import AppError, PdfNoText, PdfSupportUnavailable
from app.core.security.sanitize import drop_instruction_lines

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
PDF_PARSE_TIMEOUT_S = 5.0
PDF_PARSE_MEMORY_BYTES = 384 * 1024 * 1024
_PDF_PARSE_SLOTS = threading.BoundedSemaphore(2)

#: DOCX limits: a .docx is a zip, so its XML size is checked before it is decompressed.
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024
MAX_DOCX_ENTRIES = 2_000

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


_taxonomy_rows: tuple[dict[str, str], ...] | None = None
_taxonomy_cache: dict[str, TaxonomySkill] = {}


def _load_taxonomy() -> dict[str, TaxonomySkill]:
    """Use the same versioned reference catalogue as matching and pathways."""
    global _taxonomy_rows, _taxonomy_cache  # noqa: PLW0603
    rows = refdata.rows("taxonomy", "skills")
    if rows is not _taxonomy_rows:
        result: dict[str, TaxonomySkill] = {}
        for row in rows:
            sid = skill_taxonomy.canonical(row["id"])
            label = next((r["label"] for r in rows if r["id"] == sid), row["label"])
            aliases = tuple(
                unicodedata.normalize("NFKC", a.strip()).lower()
                for a in (row.get("aliases") or "").split("|")
                if a.strip()
            )
            if sid in result:
                old = result[sid]
                aliases = old.aliases + aliases + (old.normalised_label,)
            result[sid] = TaxonomySkill(
                sid, label, unicodedata.normalize("NFKC", label).lower(), aliases
            )
        _taxonomy_cache = result
        _taxonomy_rows = rows
        _build_alias_index.cache_clear()
    return _taxonomy_cache


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

    index = [
        _AliasEntry(
            pattern=_phrase_pattern(phrase),
            skill_id=sid,
            phrase_len=len(phrase),
            phrase=phrase.lower(),
        )
        for phrase, sid in entries
    ]
    # Action wording is only an alias for a leadership/people skill the live catalogue
    # actually contains. It must never create a new skill or imply project management.
    leadership = {"leadership", "team leadership", "people management", "team management"}
    candidates = {sid for phrase, sid in entries if phrase in leadership}
    if len(candidates) == 1:
        index.insert(
            0,
            _AliasEntry(
                pattern=re.compile(
                    r"\b(?:(?:lead|led|leading)\s+(?:a\s+|the\s+)?team|"
                    r"(?:manage|managed|managing)\s+people)\b",
                    re.IGNORECASE,
                ),
                skill_id=next(iter(candidates)),
                phrase_len=0,
            ),
        )
    return index


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
        if len(doc) > MAX_PDF_PAGES:
            raise AppError(
                "This PDF has too many pages to read as a CV.",
                status_code=422,
                code="pdf_too_many_pages",
            )
        pages: list[str] = []
        remaining = MAX_TEXT_CHARS + 1
        for page in islice(doc, MAX_PDF_PAGES):
            if pages:
                # Count only separators that will be present in the joined text.
                remaining -= 1
            text = str(page.get_text())[:remaining]
            pages.append(text)
            remaining -= len(text)
            if remaining <= 0:
                break
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


def _limit_pdf_worker() -> object:
    """Bound native parser memory/CPU before opening untrusted bytes; fail closed."""
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (PDF_PARSE_MEMORY_BYTES, PDF_PARSE_MEMORY_BYTES))
        cpu_seconds = max(1, math.ceil(PDF_PARSE_TIMEOUT_S))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        return None

    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("process_time", ctypes.c_longlong),
            ("job_time", ctypes.c_longlong),
            ("flags", wintypes.DWORD),
            ("minimum_working_set", ctypes.c_size_t),
            ("maximum_working_set", ctypes.c_size_t),
            ("active_processes", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", wintypes.DWORD),
            ("scheduling", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("basic", BasicLimits),
            ("io_counters", ctypes.c_ulonglong * 6),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process_memory", ctypes.c_size_t),
            ("peak_job_memory", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    # JOB_OBJECT_LIMIT_PROCESS_TIME | PROCESS_MEMORY | KILL_ON_JOB_CLOSE.
    limits.basic.flags = 0x2 | 0x100 | 0x2000
    limits.basic.process_time = math.ceil(PDF_PARSE_TIMEOUT_S * 10_000_000)
    limits.process_memory = PDF_PARSE_MEMORY_BYTES
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        kernel.CloseHandle(handle)
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        kernel.CloseHandle(handle)
        raise ctypes.WinError(ctypes.get_last_error())
    # Owned by this short-lived child: the OS closes it on process exit.
    return handle


def _pdf_worker(data: bytes, output: Connection) -> None:
    try:
        worker_limit = _limit_pdf_worker()
        output.send(("ok", _extract_pdf(data)))
        del worker_limit
    except AppError as exc:
        output.send(("error", (exc.message, exc.status_code, exc.code)))
    except Exception:
        output.send(
            ("error", ("PDF parsing exceeded its resource limits.", 422, "pdf_resource_limit"))
        )
    finally:
        output.close()


def extract_pdf_bounded(data: bytes) -> str:
    """Public PDF parsing with no work queue and a killable, memory-limited child."""
    if not _PDF_PARSE_SLOTS.acquire(blocking=False):
        raise AppError("PDF parsing is busy. Try again shortly.", 503, "pdf_busy")
    try:
        return _extract_pdf_process(data)
    finally:
        _PDF_PARSE_SLOTS.release()


def _extract_pdf_process(data: bytes) -> str:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_pdf_worker, args=(data, sender), daemon=True)
    deadline = time.monotonic() + PDF_PARSE_TIMEOUT_S
    try:
        process.start()
        sender.close()
        if not receiver.poll(max(0, deadline - time.monotonic())):
            raise AppError("PDF parsing took too long.", 422, "pdf_timeout")
        try:
            status, value = receiver.recv()
        except EOFError as exc:
            raise AppError(
                "PDF parsing exceeded its resource limits.", 422, "pdf_resource_limit"
            ) from exc
        if status == "error":
            raise AppError(*value)
        return str(value)
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.kill()
                process.join()
            process.close()


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
    """Apply NFKC normalisation, strip PII, collapse whitespace but keep line breaks.

    Line breaks stay because a CV line is a unit of meaning: "No formal training" on one line
    must not deny the skill on the next. All patterns are bounded to prevent ReDoS.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _PHONE_RE.sub(" ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    text = re.sub(r"[^\S\n]+", " ", text)  # spaces and tabs, not line breaks
    return re.sub(r" ?\n\s*", "\n", text).strip()


#: Where one statement about a skill ends: line breaks, bullets and list separators.
_CLAUSE_BREAK = re.compile(r"[\n;,|•·●]")


def _clause(text: str, start: int, end: int) -> str:
    """The phrase a mention belongs to, so "SQL; 8 years of Python" credits only Python."""
    left = max(0, start - _CONTEXT_CHARS)
    right = min(len(text), end + _CONTEXT_CHARS)
    before = [m.end() for m in _CLAUSE_BREAK.finditer(text, left, start)]
    after = _CLAUSE_BREAK.search(text, end, right)
    return text[(before[-1] if before else left) : (after.start() if after else right)]


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
    r"\btiada pengalaman\b|\btidak mahir\b|没有|不熟悉)[^.;,\n]{0,25}\Z",
    re.IGNORECASE,
)

# A CV records skills the person already has. A learning wish ("want to study SQL") names a
# skill they do not have yet: an intention followed by a learning verb, in EN/MS/ZH. Wording
# without a learning verb ("seeking to apply Python") keeps its skills. The wish covers the
# rest of its clause, including list items, and ends at a sentence or line boundary.
_LEARN_VERB = (
    r"(?:learn(?:ing)?|study(?:ing)?|master(?:ing)?|pick(?:ing)? up|acquir(?:e|ing)|"
    r"get(?:ting)? into|upskill(?:ing)?(?: in)?|explor(?:e|ing)|"
    r"gain(?:ing)? (?:skills?|knowledge|experience) (?:in|with))"
)
_ASPIRATION_RE = re.compile(
    r"\b(?:(?:seek(?:ing)?|want(?:ing)?|hop(?:e|ing)|wish(?:ing)?|plan(?:ning)?|"
    r"aim(?:ing)?|aspir(?:e|ing)|intend(?:ing)?|eager|keen|would like|look(?:ing)? forward)"
    r" to " + _LEARN_VERB + r"|interested in " + _LEARN_VERB + r")\b|"
    r"\b(?:ingin|mahu|hendak|bercadang(?: untuk)?|berhasrat(?: untuk)?)\s+"
    r"(?:belajar|mempelajari|menguasai|mendalami)\b|"
    r"(?:希望|想要?|计划|打算|渴望)(?:学习|学会|掌握|进修|研究)",
    re.IGNORECASE,
)
#: Where a learning wish ends: sentence punctuation followed by a space or the end (so not
#: "Node.js"), semicolons, line breaks and CJK sentence marks.
_CLAUSE_END = re.compile(r"[.!?](?=\s|$)|[;\n。；！？]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])")
# Inferred action aliases require an actual action, not an intention to perform it.
# Apply this only to action aliases so career objectives can still name existing skills.
_FUTURE_ACTION_RE = re.compile(
    r"\b(?:seeking to|want(?:ing)? to|hop(?:e|ing) to|wish to|plan(?:ning)? to|"
    r"would like to|aim(?:ing)? to|aspiring to|interested in)\s+\Z",
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


def _is_aspiration(text: str, start: int) -> bool:
    """True when a learning wish earlier in the same clause covers this mention."""
    left = 0
    for end in _CLAUSE_END.finditer(text, 0, start):
        left = end.end()
    return bool(_ASPIRATION_RE.search(text, left, start))


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
            if _is_negated(normed, s) or _is_aspiration(normed, s):
                continue
            if not entry.phrase and _FUTURE_ACTION_RE.search(normed, 0, s):
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
        level = _estimate_level(_clause(text, first_s, first_e))

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


_SKILL_HEADING = re.compile(
    r"^(?:(?:core|key|technical|professional|relevant|hard|soft|digital|tools? (?:and|&)|"
    r"technical (?:and|&) soft)\s+)?(?:skills?|competenc(?:y|ies)|expertise|"
    r"skills? (?:and|&) (?:tools|competencies|expertise|technologies)|tools (?:and|&) technologies|"
    r"kemahiran(?: teknikal| utama| insaniah)?|kepakaran|技能|专业技能|核心技能)"
    r"\s*(?:[:：]\s*(.*))?$",
    re.IGNORECASE,
)
# Any other section of a CV. A skills list ends at the first of these (or at a generic
# all-capitals heading), so job titles, employers and dates are never read as skills.
_SECTION_HEADING = re.compile(
    r"^(?:(?:professional|work|employment|relevant|career|industry|research|teaching|"
    r"volunteer(?:ing)?|leadership|internship)\s+)?(?:experience|history)|"
    r"^(?:employment|career history|work history|education|academic|qualifications?|"
    r"certifications?|certificates?|licen[cs]es?|(?:selected |key |personal )?projects?|"
    r"achievements?|awards?|honou?rs|publications?|references?|referees?|contact|"
    r"(?:professional |career |personal )?(?:summary|profile|objective)|about me|languages?|"
    r"interests?|hobbies|activities|additional information|personal (?:details|information)|"
    r"training|courses|memberships?|declaration|pengalaman|pendidikan|kelayakan|sijil|"
    r"projek|rujukan|ringkasan|bahasa|maklumat|工作经历|工作经验|教育背景|项目经历|联系方式|"
    r"个人简介|证书|语言)\b",
    re.IGNORECASE,
)
# A short line in capitals ("PROFESSIONAL EXPERIENCE", "SELECTED PROJECT") is a heading.
_CAPS_HEADING = re.compile(r"^[A-Z][A-Z &/+-]{2,40}:?$")
_LIST_SEPARATOR = re.compile(r"[,;|•●·、，；]")
_TRAILING = " \t-*–—.:;"
_BULLET = re.compile(r"^(?:[-*•●·–—▪◦‣]|\d{1,2}[.)])\s+")
_PAREN = re.compile(r"^(.*?)\s*\(([^()]{1,30})\)$")


def _is_heading(line: str) -> bool:
    if _SECTION_HEADING.match(line):
        return True
    # Short acronyms and catalogue labels are skills even when written in capitals.
    if (len(line.split()) == 1 and len(line.rstrip(":")) <= 5) or _covered(
        line, {entry.phrase for entry in _build_alias_index()}
    ):
        return False
    return bool(_CAPS_HEADING.match(line) and len(line.split()) <= 5)


def skills_section_entries(text: str) -> list[str]:
    """Every entry of the CV's skills list(s), in order, with wrapped lines rejoined.

    A section starts at a skills heading and ends at the next heading of any kind. Its lines
    are joined first, so an entry broken over two lines ("exception" / "handling.") stays one
    entry, and a word hyphenated at a line break ("val-" / "idation") is rejoined. Sub-labels
    such as "Tools: Excel, SQL" keep only the list after the colon. Future-learning entries
    are excluded with their original clause context before list separators discard it.
    """
    entries: list[str] = []
    block: list[str] = []
    active = False

    def flush() -> None:
        joined = ""
        prev = ""
        for part in block:
            bullet = _BULLET.match(part)
            if bullet:
                part = part[bullet.end() :]
            if not joined:
                joined = part
            elif joined.endswith("-") and part[:1].islower() and not bullet:
                joined = joined[:-1] + part  # a word hyphenated at the line break
            elif bullet or (not _LIST_SEPARATOR.search(prev) and len(prev.split()) <= 5):
                joined = f"{joined}; {part}"  # one entry per line
            else:
                joined = f"{joined} {part}"  # a wrapped line of a comma-separated list
            prev = part
        # A learning wish covers the later items of its own sentence ("Want to learn Rust,
        # Kubernetes") but not the next sentence ("... Kubernetes. QlikSense").
        for sentence in _SENTENCE_SPLIT.split(joined):
            offset = 0
            for item in _LIST_SEPARATOR.split(sentence):
                item_start = offset
                offset += len(item) + 1  # separators are single characters
                if _is_aspiration(sentence, item_start) or _ASPIRATION_RE.search(item):
                    continue
                if re.match(r"^[^:]{2,30}:\s", item.strip()):
                    item = item.split(":", 1)[1]
                item = re.sub(r"\s+", " ", item).strip(_TRAILING)
                if item:
                    entries.append(item)
        block.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = _SKILL_HEADING.fullmatch(line)
        if heading:
            flush()
            active = True
            if heading.group(1):
                block.append(heading.group(1))
            continue
        if not active:
            continue
        if _is_heading(line):
            flush()
            active = False
            continue
        if line:
            block.append(line)
        if len(block) >= 20:  # a skills list is short; anything longer is prose
            flush()
            active = False
    flush()
    return entries


def _covered(term: str, known: set[str]) -> bool:
    """True when the whole entry is an approved label or alias, including the common
    "Robotic process automation (RPA)" form where both halves name the same skill."""
    norm = unicodedata.normalize("NFKC", term).casefold()
    if norm in known:
        return True
    m = _PAREN.match(norm)
    return bool(m and m.group(1).strip() in known and m.group(2).strip() in known)


def unmatched_skill_terms(text: str) -> list[str]:
    """Bounded review hints from explicit skill lists, never a new skill catalogue.

    Only entries of the CV's skills section(s) are considered (see `skills_section_entries`):
    job titles, employers, dates, contact details and prose from other sections never are.
    Full entries are compared to approved aliases: a partial hit must not hide the
    unfamiliar part of a mixed phrase. Only short list entries are returned, transiently, for
    human review; matching them to the catalogue is a suggestion the person confirms.
    """
    _load_taxonomy()
    known = {entry.phrase for entry in _build_alias_index()}
    terms: list[str] = []
    seen: set[str] = set()
    for term in skills_section_entries(text):
        normalised = unicodedata.normalize("NFKC", term).casefold()
        # Reject prose, contact data, markup, numbers and long input. Unknown
        # text is still untrusted: the web renders these strings as text only.
        if (
            not 2 <= len(term) <= 64
            or _ASPIRATION_RE.search(term)
            or len(term.split()) > 6
            or not any(c.isalpha() for c in term)
            or not all(c.isalnum() or c in " +#./&()-'" for c in term)
            or _EMAIL_RE.search(term)
            or _URL_RE.search(term)
            or sum(c.isdigit() for c in term) > 4
            or _is_negated(normalised, len(normalised))
            or normalised.startswith(("no ", "without ", "not ", "tiada ", "tidak ", "没有"))
        ):
            continue
        if not _covered(term, known) and normalised not in seen:
            seen.add(normalised)
            terms.append(term)
            if len(terms) == 30:
                return terms
    return terms


def parse_cv_review(
    data: bytes | str, content_type: str = "text/plain"
) -> tuple[list[ParsedSkill], bool, list[str]]:
    """Extract once, scrub and bound the text, then return matches and review hints."""
    raw_text = extract_text(data, content_type)
    truncated_text, truncated = _truncate_text(raw_text)
    # The parser is rule-based (no model reads the CV), but a line that tries to instruct one
    # is dropped whole so a skill named inside it is never extracted or offered for review.
    cleaned = drop_instruction_lines(_clean_text(truncated_text))
    return extract_skills(cleaned), truncated, unmatched_skill_terms(cleaned)


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
    skills, truncated, _ = parse_cv_review(data, content_type)
    return skills, truncated
