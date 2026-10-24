#!/usr/bin/env python3
"""Deterministic synthetic CV fixtures for the F1 CV endpoint (Prompt 9 / item 9).

Writes the fixtures that ``tests/api/profile/test_cv_fixtures.py`` parses and that
can be uploaded by hand in Swagger at ``/docs``:

    tests/api/profile/fixtures/cvs/
        cv_aisyah.pdf, cv_weijie.pdf, cv_ravi.pdf   one per persona in the seed files
        cv_data_entry.pdf                "data entry" must not become a data skill
        cv_python_programming.pdf        "Python programming" appears exactly once
        cv_java_javascript.pdf           "Java and JavaScript" (not in the taxonomy)
        cv_scanned.pdf                   image-only page, no selectable text
        cv_long.txt                      100,000 characters with no "@"

Stdlib only. The PDFs are written by hand — PDF 1.4 with Helvetica text operators
and one FlateDecode DeviceGray image XObject — so the repository gains no
PDF-writing dependency; PyMuPDF stays a read-only dependency for the parser.

Deterministic by construction: no timestamps, no ``/CreationDate``, and the
trailer ``/ID`` is the MD5 of the file body, so re-running reproduces
byte-identical files. ``--check`` proves that without overwriting anything.

No real personal data (AGENTS.md §3): every name is invented or a synthetic
persona from ``docs/project-context.md``, every email is on ``example.com``, and
no phone number, address or ID number appears.

Usage:
    uv run --no-project python src/scripts/generate_mock_cvs.py
    uv run --no-project python src/scripts/generate_mock_cvs.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import textwrap
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "src" / "data" / "seed"
DEFAULT_OUT = REPO / "tests" / "api" / "profile" / "fixtures" / "cvs"

# Page geometry: A4 in PostScript points, one text column, fixed leading.
PAGE_W, PAGE_H = 595.0, 842.0
MARGIN_X, TOP_Y, LEADING, FONT_SIZE = 56.0, 786.0, 14.0, 11.0
MAX_CHARS_PER_LINE = 88
MAX_LINES_PER_PAGE = 48

#: Characters that must be escaped inside a PDF literal string.
_ESCAPE = {"\\": r"\\", "(": r"\(", ")": r"\)"}

#: cv_long.txt vocabulary. Deliberately free of every taxonomy label/alias token so
#: the file can only ever yield zero skill matches (asserted before writing).
_LONG_WORDS = (
    "morning train window quiet harbour paper bridge orchard lantern copper meadow "
    "shelf garden thunder picnic blanket anchor lighthouse kitchen orchard valley "
    "notebook compass saddle window shelf gully timber harvest lantern orchard"
).split()

LONG_TEXT_CHARS = 100_000

# ---------------------------------------------------------------------------
# Seed data (single source of truth: the personas and taxonomy CSVs)
# ---------------------------------------------------------------------------


def load_personas() -> list[dict[str, object]]:
    """Read the synthetic personas the CVs are generated from.

    Returns one dict per persona: ``user_id``, ``name``, ``segment``, ``email``,
    ``skills`` (taxonomy labels in seed order) and ``filler`` (a sentence that must
    never match a taxonomy alias).
    """
    names = _read_csv(SEED / "personas" / "users.csv")
    profiles = {r["user_id"]: r for r in _read_csv(SEED / "personas" / "profiles.csv")}
    skills = _read_csv(SEED / "personas" / "user_skills.csv")
    labels = {r["id"]: r["label"] for r in _read_csv(SEED / "taxonomy" / "skills.csv")}

    personas: list[dict[str, object]] = []
    for row in names:
        uid = row["id"]
        profile = profiles.get(uid)
        if profile is None:
            continue
        owned = [s for s in skills if s["user_id"] == uid]
        personas.append(
            {
                "user_id": uid,
                "name": row["display_name"],
                "segment": profile["segment"],
                "email": f"{uid}@example.com",
                "skills": [labels[s["skill_id"]] for s in owned],
                "filler": _PERSONA_FILLER[uid],
            }
        )
    return personas


_PERSONA_FILLER = {
    "aisyah": "Six years on a counter team in Kuala Lumpur, then two years in a back office.",
    "weijie": "Fresh diploma holder, weekend club volunteer, keen on a first full-time role.",
    "ravi": "Supervisor of a small depot crew for four years, roster owner for the night shift.",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def taxonomy_terms() -> list[str]:
    """Every label and alias in the taxonomy, lowercased (for the no-match guard)."""
    terms: list[str] = []
    for row in _read_csv(SEED / "taxonomy" / "skills.csv"):
        cells = [row["label"], *(row.get("aliases") or "").split("|")]
        terms.extend(c.strip().lower() for c in cells if c.strip())
    return terms


# ---------------------------------------------------------------------------
# CV documents (content only; the PDF layer below never sees the personas)
# ---------------------------------------------------------------------------


def persona_cv_text(persona: dict[str, object]) -> str:
    """Plain-text CV for one synthetic persona: same name, segment and skills."""
    lines = [
        str(persona["name"]),
        "Curriculum Vitae - synthetic demo record",
        f"{persona['email']} | Kuala Lumpur, Malaysia",
        "",
        "Profile",
        f"Segment: {persona['segment']}",
        str(persona["filler"]),
        "",
        "Skills",
    ]
    lines.extend(f"- {label}" for label in persona["skills"])  # type: ignore[union-attr]
    lines += ["", "Education", "Diploma of Science, part-time study, completed 2021.", ""]
    return "\n".join(lines)


def data_entry_cv_text() -> str:
    """Fixture text: the phrase "data entry" must not resolve to any skill."""
    return "\n".join(
        [
            "Nurul Hidayah",
            "Curriculum Vitae - synthetic demo record",
            "nurul@example.com",
            "",
            "Objective",
            "Clerk applying for a data entry position in a shared service centre.",
            "",
            "Work history",
            "Counter clerk, three years. Keystroke accuracy 85 words per minute.",
            "Duties: filing, form handling, shift cover, typing.",
            "",
        ]
    )


def python_programming_cv_text() -> str:
    """Fixture text: "Python programming" appears exactly once -> one python hit."""
    return "\n".join(
        [
            "Siti Aminah",
            "Curriculum Vitae - synthetic demo record",
            "siti@example.com",
            "",
            "Summary",
            "Skilled in Python programming.",
            "",
            "Interests",
            "Chess, running, home cooking.",
            "",
        ]
    )


def java_javascript_cv_text() -> str:
    """Fixture text: "Java and JavaScript" - neither is in the taxonomy."""
    return "\n".join(
        [
            "Ahmad Faizal",
            "Curriculum Vitae - synthetic demo record",
            "ahmad@example.com",
            "",
            "Summary",
            "Weekend coursework covering Java and JavaScript basics.",
            "",
            "Interests",
            "Cycling, film photography, board games.",
            "",
        ]
    )


def long_text() -> str:
    """Exactly 100,000 characters containing no "@" and no taxonomy term."""
    out: list[str] = []
    total = 0
    i = 0
    while total < LONG_TEXT_CHARS:
        word = _LONG_WORDS[i % len(_LONG_WORDS)] + " "
        out.append(word)
        total += len(word)
        if i % 11 == 10:
            out.append("\n")
            total += 1
        i += 1
    text = "".join(out)[:LONG_TEXT_CHARS]
    assert "@" not in text, "fixture must contain no @"
    assert len(text) == LONG_TEXT_CHARS, f"expected {LONG_TEXT_CHARS} chars, got {len(text)}"
    lowered = text.lower()
    hits = [t for t in taxonomy_terms() if t in lowered]
    assert not hits, f"long-text fixture unexpectedly contains taxonomy terms: {hits}"
    return text


# ---------------------------------------------------------------------------
# Minimal PDF 1.4 writer (stdlib only)
# ---------------------------------------------------------------------------


def _literal(text: str) -> bytes:
    """Encode one literal-string operand; PDF literals only need \\ ( ) escaped."""
    escaped = "".join(_ESCAPE.get(ch, ch) for ch in text)
    return f"({escaped})".encode("cp1252")


def _wrap(text: str) -> list[str]:
    """Split into display lines, wrapping on word boundaries only."""
    lines: list[str] = []
    for raw in text.split("\n"):
        if not raw.strip():
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                raw,
                width=MAX_CHARS_PER_LINE,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return lines


def _text_page_ops(lines: list[str]) -> bytes:
    ops = [
        b"BT",
        f"/F1 {int(FONT_SIZE)} Tf".encode(),
        f"{int(LEADING)} TL".encode(),
        f"1 0 0 1 {MARGIN_X:g} {TOP_Y:g} Tm".encode(),
    ]
    for line in lines:
        ops.append(_literal(line))
        ops.append(b"Tj")
        ops.append(b"T*")
    ops.append(b"ET")
    return b"\n".join(ops)


def _stream(data: bytes, extra: str = "") -> bytes:
    head = f"<< /Length {len(data)}{extra} >>\nstream\n".encode("ascii")
    return head + data + b"\nendstream"


def _assemble(objects: list[bytes]) -> bytes:
    """Write object bodies (1-based) plus xref and trailer, with a content-derived ID."""
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_at = len(out)
    size = len(objects) + 1
    out += f"xref\n0 {size}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("ascii")

    digest = hashlib.md5(bytes(out), usedforsecurity=False).hexdigest()
    out += (
        f"trailer\n<< /Size {size} /Root 1 0 R "
        f"/ID [<{digest}> <{digest}>] >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def pdf_from_text(text: str) -> bytes:
    """Build a multi-page text PDF. Helvetica only, no compression, byte-stable."""
    lines = _wrap(text)
    pages = [lines[i : i + MAX_LINES_PER_PAGE] for i in range(0, len(lines), MAX_LINES_PER_PAGE)]
    page_count = len(pages)
    first_page = 4
    first_content = first_page + page_count
    kids = " ".join(f"{first_page + i} 0 R" for i in range(page_count))

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i in range(page_count):
        content_ref = first_content + i
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:g} {PAGE_H:g}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_ref} 0 R >>"
            ).encode("ascii")
        )
    for i in range(page_count):
        objects.append(_stream(_text_page_ops(pages[i])))
    return _assemble(objects)


def scanned_page_bitmap(width: int = 100, height: int = 140) -> bytes:
    """Deterministic DeviceGray sample set that *looks* like a scanned page."""
    rows = bytearray()
    for y in range(height):
        on_line = (y % 12) < 7  # a fake text line
        for x in range(width):
            ink = on_line and (x % 9) < 6 and not (x % 9 == 0 and y % 3 == 0)
            rows.append(0x2A if ink else 0xF6)
    return bytes(rows)


def pdf_from_image(width: int = 100, height: int = 140) -> bytes:
    """Build an image-only PDF: one XObject, zero text operators, no selectable text."""
    samples = zlib.compress(scanned_page_bitmap(width, height), level=9)
    draw = f"q {PAGE_W - 2 * MARGIN_X:g} 0 0 {PAGE_H - 2 * MARGIN_X:g} {MARGIN_X:g} 56 cm /Im0 Do Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:g} {PAGE_H:g}] "
            "/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode("ascii"),
        _stream(draw.encode("ascii")),
        _stream(
            samples,
            extra=(
                f" /Filter /FlateDecode /Type /XObject /Subtype /Image /Width {width} "
                f"/Height {height} /ColorSpace /DeviceGray /BitsPerComponent 8"
            ),
        ),
    ]
    return _assemble(objects)


# ---------------------------------------------------------------------------
# Fixture manifest and file writing
# ---------------------------------------------------------------------------


def fixtures() -> dict[str, bytes]:
    """Every fixture file as ``{filename: bytes}`` — deterministic, in sorted order."""
    files: dict[str, bytes] = {}
    for persona in load_personas():
        uid = str(persona["user_id"])
        files[f"cv_{uid}.pdf"] = pdf_from_text(persona_cv_text(persona))
    files["cv_data_entry.pdf"] = pdf_from_text(data_entry_cv_text())
    files["cv_python_programming.pdf"] = pdf_from_text(python_programming_cv_text())
    files["cv_java_javascript.pdf"] = pdf_from_text(java_javascript_cv_text())
    files["cv_scanned.pdf"] = pdf_from_image()
    files["cv_long.txt"] = long_text().encode("utf-8")
    return {name: files[name] for name in sorted(files)}


def _extracted_ids(payload: bytes, content_type: str) -> set[str]:
    """Parse with the production parser, if importable (used by --verify only)."""
    from app.features.profile.cv_parser import parse_cv

    parsed, _ = parse_cv(payload, content_type)
    return {s.skill_id for s in parsed}


def expected_ids(name: str) -> set[str]:
    """Skill IDs each fixture must (or must not) resolve to, from the seed files."""
    from app.features.matching.personas import load_persona_profile

    uid = name.removeprefix("cv_").removesuffix(".pdf")
    profile = load_persona_profile(uid)
    if profile is None:
        raise ValueError(f"unknown persona fixture {name}")
    return set(profile.skills)


EDGE_NEGATIVES = {
    "cv_data_entry.pdf": set(),
    "cv_java_javascript.pdf": set(),
    "cv_long.txt": set(),
}


def verify(out: Path) -> None:
    """Re-parse the written fixtures with the production parser and assert the contract."""
    for uid in sorted(str(p["user_id"]) for p in load_personas()):
        name = f"cv_{uid}.pdf"
        found = _extracted_ids((out / name).read_bytes(), "application/pdf")
        assert found == expected_ids(name), f"{name} parsed as {sorted(found)}"

    once = _extracted_ids((out / "cv_python_programming.pdf").read_bytes(), "application/pdf")
    assert once == {"python"}, f"cv_python_programming.pdf parsed as {sorted(once)}"

    for name, want in EDGE_NEGATIVES.items():
        ctype = "application/pdf" if name.endswith(".pdf") else "text/plain"
        found = _extracted_ids((out / name).read_bytes(), ctype)
        assert found == want, f"{name} must match nothing, matched {sorted(found)}"

    from app.core.errors import AppError
    from app.features.profile.cv_parser import extract_text

    try:
        extract_text((out / "cv_scanned.pdf").read_bytes(), "application/pdf")
        raise AssertionError("cv_scanned.pdf must expose no selectable text")
    except AppError as exc:
        assert (exc.status_code, exc.code) == (422, "pdf_no_text"), f"got {exc.code}"

    payload = (out / "cv_long.txt").read_bytes()
    assert len(payload) == LONG_TEXT_CHARS, f"cv_long.txt is {len(payload)} bytes"
    assert payload.count(b"@") == 0, "cv_long.txt must contain no @"


def write_fixtures(out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, payload in fixtures().items():
        target = out / name
        target.write_bytes(payload)
        written.append(name)
    return written


def check_fixtures(out: Path) -> list[str]:
    """Return the names of files on disk that differ from a fresh generation."""
    stale: list[str] = []
    for name, payload in fixtures().items():
        target = out / name
        if not target.exists() or target.read_bytes() != payload:
            stale.append(name)
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="fixture output directory")
    parser.add_argument(
        "--check", action="store_true", help="report drift instead of writing (CI mode)"
    )
    parser.add_argument(
        "--verify", action="store_true", help="after writing, re-parse with the real parser"
    )
    args = parser.parse_args(argv)

    if args.check:
        stale = check_fixtures(args.out)
        if stale:
            print(f"STALE ({len(stale)}): {', '.join(stale)}")
            print("regenerate with: uv run --no-project python src/scripts/generate_mock_cvs.py")
            return 1
        print(f"deterministic: {len(fixtures())} fixtures match {args.out}")
        return 0

    written = write_fixtures(args.out)
    print(f"wrote {len(written)} fixtures to {args.out}")
    for name in written:
        print(f"  {name}  {(args.out / name).stat().st_size:,} bytes")
    if args.verify:
        import sys

        sys.path.insert(0, str(REPO / "src" / "api"))
        verify(args.out)
        print("verify: every fixture parses exactly as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
