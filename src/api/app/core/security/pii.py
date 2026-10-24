"""Deterministic PII redaction before any text reaches an LLM or a log. From KerjaCerdas.

Prompt instructions ("do not repeat personal data") can fail, so fixed rules run first.
Adapted to Malaysian formats:

    email                      -> [email]
    MyKad NRIC 900101-14-5678  -> [nric]   (also the 12-digit form without dashes)
    passport A12345678         -> [passport]
    phone +60 12-345 6789      -> [phone]  (mobile, landline, international)

Phone patterns are specific on purpose: KerjaCerdas's generic "8+ digits with separators"
rule also redacted date ranges such as 2019-2024, which a CV needs.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NRIC = re.compile(r"(?<!\d)\d{6}-\d{2}-\d{4}(?!\d)|(?<!\d)\d{12}(?!\d)")
_PASSPORT = re.compile(r"\b[AHK]\d{8}\b")
_PHONE_MY = re.compile(
    r"(?<![\w+])(?:\+?60[\s-]?|0)(?:1\d[\s-]?\d{3,4}[\s-]?\d{4}|[3-9][\s-]?\d{3,4}[\s-]?\d{4})(?!\d)"
)
_PHONE_INTL = re.compile(r"(?<!\w)\+\d{1,3}[\s-]?\d[\d\s-]{6,}\d(?!\d)")

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (_EMAIL, "[email]"),
    (_NRIC, "[nric]"),
    (_PASSPORT, "[passport]"),
    (_PHONE_MY, "[phone]"),
    (_PHONE_INTL, "[phone]"),
)


def redact_text(text: str) -> str:
    for pattern, label in _RULES:
        text = pattern.sub(label, text)
    return text


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern, _ in _RULES)
