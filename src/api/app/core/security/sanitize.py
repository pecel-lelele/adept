"""Input sanitisation for text that reaches an LLM or is stored by Adept.

- `sanitize_text`: strict; raises 422 when user-typed text contains a prompt-injection pattern.
- `clean_extracted_text`: soft; for document text (CVs) it neutralises the same patterns
  with `[filtered]` instead of rejecting the upload.
- `sanitize_filename`: safe characters only, no path traversal.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

from app.core.errors import AppError

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"^\s*(system|assistant|developer)\s*:", re.I | re.M),
    re.compile(r"<\s*(?:script|iframe|object|embed|form|link|meta|style)", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"\\u003c|\\u003e|%3C|%3E", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"\bDAN\s*mode\b", re.I),
    re.compile(r"(pretend|act)\s+as\s+(if\s+you\s+are|an?\s+)", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"(base64|hex)\s*decode", re.I),
    re.compile(r"(\r?\n){6,}"),
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ALL_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DANGEROUS_HTML = re.compile(
    r"</?(?:script|iframe|object|embed|form|input|button|style|meta|link)[^>]*>", re.I
)
_UNSAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._\- ]")


def _strip(text: str, max_length: int, allow_newlines: bool) -> str:
    text = text[:max_length]
    text = (_CONTROL_CHARS if allow_newlines else _ALL_CONTROL).sub("", text)
    return _DANGEROUS_HTML.sub("", text)


def find_injection(text: str) -> str | None:
    """Return the first matching injection pattern, or None."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def sanitize_text(
    text: str, *, max_length: int = 4_000, allow_newlines: bool = True, field: str = "input"
) -> str:
    cleaned = _strip(text, max_length, allow_newlines)
    if find_injection(cleaned):
        raise AppError(
            f"Field '{field}' contains disallowed content.",
            status_code=422,
            code="disallowed_content",
        )
    return cleaned.strip()


def clean_extracted_text(text: str, *, max_length: int = 20_000) -> str:
    cleaned = _strip(text, max_length, allow_newlines=True)
    for pattern in INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    return cleaned.strip()


#: Patterns that try to instruct a model, as opposed to markup or encoding tricks.
_INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    p for p in INJECTION_PATTERNS if not re.search(r"script|javascript|u003c|\\r\?\\n", p.pattern)
)


def drop_instruction_lines(text: str) -> str:
    """Remove whole lines that try to instruct a model ("Ignore previous instructions...").

    Used on document text such as CVs: dropping the line, not just the phrase, keeps a skill
    named inside the injected instruction from being extracted ("...add Kubernetes as expert").
    """
    return "\n".join(
        line
        for line in text.split("\n")
        if not any(pattern.search(line) for pattern in _INSTRUCTION_PATTERNS)
    )


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1][:max_length]
    name = _UNSAFE_FILENAME.sub("_", name).replace("..", "_").strip(" .")
    return name or "upload"


SanitizedStr = Annotated[str, AfterValidator(lambda v: sanitize_text(v, max_length=2_000))]
