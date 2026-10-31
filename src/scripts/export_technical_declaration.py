"""Export the tracked declaration Markdown with the existing PyMuPDF dependency.

Run from the repository root. No network, model, or office automation is needed.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/submission/submission-technical-declaration.md"
OUTPUT = ROOT / "submission/SDC2026_Pecel-Lele_TechDeclaration.pdf"


def inline(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", value)


def markdown_html(text: str) -> str:
    """Render the small Markdown subset shared by the three public documents."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    output: list[str] = []
    paragraph: list[str] = []
    table: list[str] = []
    code: list[str] | None = None

    def flush() -> None:
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()
        if table:
            output.append("<table>")
            for i, row in enumerate(table):
                if re.fullmatch(r"[| :\-]+", row):
                    continue
                cell = "th" if i == 0 else "td"
                output.append(
                    "<tr>"
                    + "".join(
                        f"<{cell}>{inline(c.strip())}</{cell}>" for c in row.strip("|").split("|")
                    )
                    + "</tr>"
                )
            output.append("</table>")
            table.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                output.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        line = line.strip().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
        if line.startswith("|"):
            if paragraph:
                flush()
            table.append(line)
        elif line.startswith("#"):
            flush()
            level = min(len(line) - len(line.lstrip("#")), 4)
            output.append(f"<h{level}>{inline(line.lstrip('# ').strip())}</h{level}>")
        elif line.startswith("- [ ]") or line.startswith("- [x]"):
            flush()
            output.append("<p>" + inline(line[2:]) + "</p>")
        elif line.startswith("- "):
            flush()
            output.append("<p>• " + inline(line[2:]) + "</p>")
        elif re.match(r"^\d+\. ", line):
            flush()
            output.append("<p>" + inline(line) + "</p>")
        elif not line:
            flush()
        else:
            if table:
                flush()
            paragraph.append(line)
    flush()
    return "<html><body>" + "\n".join(output) + "</body></html>"


def render_pdf(source: Path, output: Path, title: str) -> None:
    story = pymupdf.Story(
        markdown_html(source.read_text("utf-8")),
        user_css="""
        body { font-family: sans-serif; font-size: 9pt; line-height: 1.35; color: #24332c; }
        h1 { font-size: 22pt; color: #174a39; }
        h2 { font-size: 14pt; color: #174a39; margin-top: 18pt; }
        h3 { font-size: 11pt; color: #174a39; margin-top: 12pt; }
        p { margin: 6pt 0; }
        table { width: 100%; border-collapse: collapse; margin: 8pt 0; }
        th, td { border: 0.5pt solid #c8d6cd; padding: 5pt; font-size: 8pt; }
        th { font-weight: bold; }
        a { color: #176148; }
        code { font-size: 8pt; }
        pre { font-family: monospace; font-size: 8pt; white-space: pre-wrap;
              background-color: #f2f7f1; padding: 8pt; }
    """,
    )
    media = pymupdf.paper_rect("a4")
    body = pymupdf.Rect(38, 40, media.width - 38, media.height - 42)

    def rectangles(number: int, filled: pymupdf.Rect) -> tuple:
        return media, body, None

    document = story.write_with_links(rectangles)
    for i, page in enumerate(document):
        page.wrap_contents()
        page.insert_text(
            (38, media.height - 23),
            f"31 October 2026 | Unsigned draft | {i + 1} / {len(document)}",
            fontsize=7,
            color=(0.35, 0.4, 0.36),
        )
    document.set_metadata(
        {
            "title": title,
            "author": "Pecel Lele",
            "subject": "Unsigned source-grounded draft, 31 October 2026",
        }
    )
    document.save(output, garbage=4, deflate=True)
    print(f"Exported {len(document)} pages to {output}")


def main() -> None:
    render_pdf(SOURCE, OUTPUT, "Adept Technical Tools Declaration")


if __name__ == "__main__":
    main()
