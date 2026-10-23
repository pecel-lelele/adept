"""Check Python code fences in bundled Markdown guides for syntax errors."""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PYTHON_LANGUAGES = {"py", "python", "python3"}
MARKDOWN_SUFFIXES = {".md", ".mdx", ".markdown"}
DEFAULT_GUIDE_ROOTS = (Path(".local/skills"), Path(".local/secondary_skills"))


@dataclass(frozen=True)
class PythonFence:
    start_line: int
    source: str
    closed: bool


def _python_language(info: str) -> bool:
    language = info.strip().split(maxsplit=1)
    return bool(language and language[0].lower() in PYTHON_LANGUAGES)


def python_fences(markdown: str) -> Iterator[PythonFence]:
    """Yield Python fenced blocks, including unclosed blocks for diagnostics."""
    opening_fence = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
    lines = markdown.splitlines()
    fence_marker: str | None = None
    is_python = False
    start_line = 0
    code_lines: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if fence_marker is None:
            opening = opening_fence.match(line)
            if not opening:
                continue
            fence_marker = opening.group(1)
            is_python = _python_language(opening.group(2))
            start_line = line_number + 1
            code_lines = []
            continue

        closing = re.fullmatch(
            rf" {{0,3}}{re.escape(fence_marker[0])}{{{len(fence_marker)},}}[ \t]*",
            line,
        )
        if closing:
            if is_python:
                yield PythonFence(start_line, "\n".join(code_lines), closed=True)
            fence_marker = None
            is_python = False
            continue

        if is_python:
            code_lines.append(line)

    if fence_marker is not None and is_python:
        yield PythonFence(start_line, "\n".join(code_lines), closed=False)


def check_file(path: Path) -> int:
    """Check each Python fence in one Markdown file; return the error count."""
    display_path = str(path)
    markdown = path.read_text(encoding="utf-8")
    errors = 0

    for fence in python_fences(markdown):
        if not fence.closed:
            print(
                f"{display_path}:{fence.start_line - 1}: error: unclosed Python code fence",
                file=sys.stderr,
            )
            errors += 1
            continue
        try:
            tree = ast.parse(
                fence.source,
                filename=display_path,
                feature_version=(3, 11),
            )
            compile(tree, display_path, "exec")
        except SyntaxError as exc:
            line = fence.start_line + (exc.lineno or 1) - 1
            message = exc.msg or "invalid Python syntax"
            print(f"{display_path}:{line}: error: {message}", file=sys.stderr)
            errors += 1

    return errors


def markdown_files(roots: tuple[Path, ...]) -> Iterator[Path]:
    """Yield Markdown files under the given guide roots in stable order."""
    for root in roots:
        if not root.is_dir():
            raise FileNotFoundError(f"guide directory does not exist: {root}")
        yield from sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES
        )


def main() -> int:
    try:
        files = tuple(markdown_files(DEFAULT_GUIDE_ROOTS))
    except FileNotFoundError as exc:
        print(f"Guide Python check failed: {exc}", file=sys.stderr)
        return 2

    errors = sum(check_file(path) for path in files)
    if errors:
        print(f"Guide Python check failed: {errors} syntax error(s) found.", file=sys.stderr)
        return 1

    print(f"Guide Python check passed ({len(files)} Markdown files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
