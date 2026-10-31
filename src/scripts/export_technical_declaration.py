"""Export the declaration in the organisers' template layout (see ``template_pdf``).

Run from the repository root. No network, model, or office automation is needed.
``render_pdf`` is the styled A4 layout used by ``export_prd.py``.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/submission/submission-technical-declaration.md"
OUTPUT = ROOT / "submission/SDC2026_Pecel-Lele_TechDeclaration.pdf"

TEAM = "Pecel Lele"
PRODUCT = "Adept"
EVENT = "SDC XMUM Hackathon 2026"

GREEN = "#174a39"
GREEN_2 = "#176148"
INK = "#1f2d27"
MUTED = "#5f6f67"

MM = 72 / 25.4
MARGIN_X = 20 * MM
MARGIN_TOP = 22 * MM
MARGIN_BOTTOM = 20 * MM

BODY_CSS = f"""
body {{ font-family: sans-serif; font-size: 9.6pt; line-height: 1.42; color: {INK}; }}
h2 {{ font-size: 13.5pt; color: {GREEN}; margin: 16pt 0 6pt 0; padding-bottom: 3pt;
      border-bottom: 0.8pt solid #b9d0c3; }}
h3 {{ font-size: 11pt; color: {GREEN_2}; margin: 12pt 0 4pt 0; }}
h4 {{ font-size: 10pt; color: {GREEN_2}; margin: 10pt 0 3pt 0; }}
p {{ margin: 0 0 6pt 0; }}
ul, ol {{ margin: 0 0 6pt 0; padding-left: 14pt; }}
li {{ margin: 0 0 3pt 0; }}
ul.check {{ list-style-type: none; padding-left: 2pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 4pt 0 10pt 0; font-size: 8.5pt; }}
th {{ font-weight: bold; color: {GREEN}; border-top: 1.4pt solid {GREEN};
      text-align: left; padding: 4pt 5pt; border-bottom: 1pt solid {GREEN}; }}
td {{ line-height: 1.32; padding: 4pt 5pt; border-bottom: 0.5pt solid #d5e2da; }}
.r {{ text-align: right; }}
a:link {{ color: {GREEN_2}; text-decoration: none; }}
p.sign {{ margin: 14pt 0 4pt 0; color: {MUTED}; }}
code {{ font-family: monospace; font-size: 8.4pt; color: {GREEN}; }}
pre {{ font-family: monospace; font-size: 7.8pt; line-height: 1.25; white-space: pre;
       border-left: 2pt solid #b9d0c3; padding: 2pt 0 2pt 8pt; margin: 4pt 0 8pt 0; }}
.box {{ color: {GREEN}; font-size: 10.5pt; }}
.ph {{ color: {MUTED}; font-style: italic; }}
.ref {{ color: {GREEN_2}; }}
td b, td i, td a, td span, td code, th b, th code {{ font-size: 8.5pt; }}
"""

COVER_CSS = """
* { font-family: sans-serif; }
.eyebrow { font-size: 8pt; color: #a9d3bd; font-weight: bold; margin: 0 0 6pt 0; }
h1 { font-size: 24pt; line-height: 1.15; color: #ffffff; margin: 0 0 6pt 0; }
.sub { font-size: 12pt; line-height: 1.3; color: #ffffff; margin: 0 0 6pt 0; }
.meta { font-size: 9pt; line-height: 1.35; color: #d7ebe0; margin: 0 0 1.5pt 0; }
b { color: #ffffff; }
code { font-family: monospace; }
"""


def inline(value: str) -> str:
    """Render inline Markdown (code, links, bold, italics, checkboxes, placeholders)."""
    kept: list[str] = []

    def keep(fragment: str) -> str:
        kept.append(fragment)
        return f"\x00{len(kept) - 1}\x00"

    value = value.replace("‑", "-")
    value = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1))}</code>"), value)
    value = re.sub(
        r"\[([^\]]+)\]\((\S+?)\)",
        lambda m: keep(f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>'),
        value,
    )
    value = re.sub(
        r"https?://[^\s<>()|]*[^\s<>()|.,;:]",
        lambda m: keep(f'<a href="{html.escape(m.group(0))}">{html.escape(m.group(0))}</a>'),
        value,
    )
    value = re.sub(
        r"\[( |x|X)\]",
        lambda m: keep(f'<span class="box">{"&#9744;" if m.group(1) == " " else "&#9745;"}</span>'),
        value,
    )
    value = re.sub(
        r"\[((?:To be|Signature|Date)[^\]]*)\]",
        lambda m: keep(f'<span class="ph">{html.escape(m.group(1))}</span>'),
        value,
    )
    value = re.sub(
        r"\[([SA]\d+)\]", lambda m: keep(f'<span class="ref">[{m.group(1)}]</span>'), value
    )
    value = html.escape(value, quote=False)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<i>\1</i>", value)
    value = re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], value)
    # Space out inline choices such as "[ ] Yes [ ] No".
    return re.sub(r"(\S) (<span class=\"box\">)", r"\1&nbsp;&nbsp;&nbsp;&nbsp;\2", value)


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in rows]
    align: list[str] = []
    body = []
    for row in cells:
        if all(re.fullmatch(r":?-{2,}:?", c) for c in row if c):
            align = ["r" if c.endswith(":") and not c.startswith(":") else "" for c in row]
            continue
        body.append(row)
    out = ["<table>"]
    for i, row in enumerate(body):
        tag = "th" if i == 0 else "td"
        tds = []
        for j, cell in enumerate(row):
            a = align[j] if j < len(align) else ""
            attr = f' class="{a}"' if a else ""
            tds.append(f"<{tag}{attr}>{inline(cell)}</{tag}>")
        row_id = ' id="@row@"' if i == 1 else ""  # first data row, tracked for page breaks
        out.append(f"<tr{row_id}>" + "".join(tds) + "</tr>")
    out.append("</table>")
    return "".join(out)


def markdown_html(text: str, page_breaks: frozenset[int] = frozenset()) -> tuple[str, set[int]]:
    """Render the small Markdown subset shared by the three public documents.

    Every block gets an ``id="b<n>"`` so layout can detect headings stranded at a page
    foot; ``page_breaks`` holds block numbers that must start a new page. Returns the
    HTML and the block numbers that are headings.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    output: list[str] = []
    paragraph: list[str] = []
    table: list[str] = []
    items: list[str] = []
    headings: set[int] = set()
    list_kind = ""
    code: list[str] | None = None

    def emit(fragment: str) -> None:
        number = len(output)
        fragment = re.sub(r"^<(\w+)", rf'<\1 id="b{number}"', fragment, count=1)
        fragment = fragment.replace('id="@row@"', f'id="b{number}r"')
        if number in page_breaks:
            fragment = f'<div style="page-break-before: always">{fragment}</div>'
        output.append(fragment)

    def flush() -> None:
        nonlocal list_kind
        if paragraph:
            joined = " ".join(paragraph)
            if joined in ("[Signature]", "[Date]"):  # organiser sign-off lines
                rule = "_" * (46 if joined == "[Signature]" else 51)
                emit(f'<p class="sign">{joined.strip("[]")}:&nbsp;&nbsp;{rule}</p>')
            else:
                emit("<p>" + inline(joined) + "</p>")
            paragraph.clear()
        if table:
            emit(_table(table))
            table.clear()
        if items:
            tag = "ol" if list_kind == "ol" else "ul"
            cls = ' class="check"' if list_kind == "check" else ""
            emit(f"<{tag}{cls}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>")
            items.clear()
            list_kind = ""

    def add_item(kind: str, content: str) -> None:
        nonlocal list_kind
        if list_kind != kind:
            flush()
            list_kind = kind
        items.append(inline(content))

    for raw in text.splitlines():
        if raw.strip().startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                emit("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code = None
            continue
        if code is not None:
            code.append(raw)
            continue
        line = raw.strip()
        if line.startswith("|"):
            if paragraph or items:
                flush()
            table.append(line)
        elif line.startswith("#"):
            flush()
            level = min(len(line) - len(line.lstrip("#")), 4)
            headings.add(len(output))
            emit(f"<h{level}>{inline(line.lstrip('# ').strip())}</h{level}>")
        elif re.match(r"^- \[( |x|X)\] ", line):
            add_item("check", line[2:])
        elif line.startswith("- "):
            add_item("ul", line[2:])
        elif re.match(r"^\d+\. ", line):
            add_item("ol", re.sub(r"^\d+\. ", "", line))
        elif not line:
            flush()
        else:
            if table or items:
                flush()
            paragraph.append(line)
    flush()
    return "<html><body>" + "\n".join(output) + "</body></html>", headings


def split_cover(text: str) -> tuple[str, list[str], str]:
    """Return the H1 title, the lines before the first section, and the remaining body."""
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("## "))
    head = [line.strip() for line in lines[:first] if line.strip()]
    title = head[0].lstrip("# ").strip() if head and head[0].startswith("# ") else ""
    return title, head[1:] if title else head, "\n".join(lines[first:])


def cover_html(title: str, lines: list[str]) -> str:
    parts = [f'<p class="eyebrow">{PRODUCT.upper()} &#183; TEAM {TEAM.upper()}</p>']
    parts.append(f"<h1>{inline(title)}</h1>")
    for i, line in enumerate(lines):
        cls = "sub" if i == 0 else "meta"
        parts.append(f'<p class="{cls}">{inline(line)}</p>')
    return "".join(parts)


def _layout(body_html: str, first_top: float) -> tuple[pymupdf.Document, dict[str, int]]:
    """Lay out the body; return the document and the page of each tracked block id."""
    media = pymupdf.paper_rect("a4")
    bottom = media.height - MARGIN_BOTTOM

    def rectangles(number: int, filled: pymupdf.Rect) -> tuple:
        top = first_top if number == 0 else MARGIN_TOP
        return media, pymupdf.Rect(MARGIN_X, top, media.width - MARGIN_X, bottom), None

    pages: dict[str, int] = {}

    def record(pos: pymupdf.ElementPosition) -> None:
        ident = pos.id or ""
        if re.fullmatch(r"b\d+r?", ident) and pos.open_close & 1:
            pages.setdefault(ident, int(pos.page_num))

    story = pymupdf.Story(body_html, user_css=BODY_CSS)
    document = story.write_with_links(rectangles, positionfn=record)
    return document, pages


def _stranded_blocks(pages: dict[str, int], headings: set[int]) -> set[int]:
    """Blocks left alone at a page foot: a heading whose following content starts on a
    later page, or a table whose header row is separated from its first data row."""

    def content_page(block: int) -> int:
        return pages.get(f"b{block}r", pages.get(f"b{block}", 0))

    stranded = set()
    for key, page in pages.items():
        if key.endswith("r"):
            continue
        block = int(key[1:])
        if block in headings and f"b{block + 1}" in pages and content_page(block + 1) > page:
            stranded.add(block)
        elif content_page(block) > page:
            stranded.add(block)
    return stranded


def _header_footer(document: pymupdf.Document, header: str) -> None:
    font = pymupdf.Font("helv")
    bold = pymupdf.Font("hebo")
    muted = (0.40, 0.45, 0.42)
    rule = (0.76, 0.84, 0.80)
    total = len(document)
    for i, page in enumerate(document):
        page.wrap_contents()
        width, height = page.rect.width, page.rect.height
        left, right = MARGIN_X, width - MARGIN_X
        writer = pymupdf.TextWriter(page.rect)
        if i:
            writer.append((left, 36), f"{PRODUCT}  ", font=bold, fontsize=7.8)
            writer.append(writer.last_point, f"|  {header}", font=font, fontsize=7.8)
            event_w = font.text_length(EVENT, fontsize=7.8)
            writer.append((right - event_w, 36), EVENT, font=font, fontsize=7.8)
            page.draw_line((left, 42), (right, 42), color=rule, width=0.6)
        foot_y = height - 30
        page.draw_line((left, foot_y - 11), (right, foot_y - 11), color=rule, width=0.6)
        writer.append((left, foot_y), f"Team {TEAM} · {PRODUCT}", font=font, fontsize=7.8)
        label = f"Page {i + 1} of {total}"
        writer.append(
            (right - font.text_length(label, fontsize=7.8), foot_y), label, font=font, fontsize=7.8
        )
        writer.write_text(page, color=muted)


def render_pdf(source: Path, output: Path, title: str, header: str | None = None) -> None:
    """Render a tracked Markdown document to a styled A4 PDF with cover, header and footer."""
    cover_title, cover_lines, body = split_cover(source.read_text("utf-8"))
    media = pymupdf.paper_rect("a4")
    cover = cover_html(cover_title or title, cover_lines)
    band_pad = 16 * MM
    cover_rect_height = 400.0

    probe = pymupdf.open()
    spare, _ = probe.new_page(width=media.width, height=media.height).insert_htmlbox(
        pymupdf.Rect(MARGIN_X, 0, media.width - MARGIN_X, cover_rect_height), cover, css=COVER_CSS
    )
    probe.close()
    cover_height = cover_rect_height - spare
    band_bottom = band_pad + cover_height + 10 * MM
    first_top = band_bottom + 3 * MM

    breaks: frozenset[int] = frozenset()
    for _ in range(40):
        body_html, headings = markdown_html(body, breaks)
        document, pages = _layout(body_html, first_top)
        stranded = sorted(_stranded_blocks(pages, headings))
        if not stranded:
            break
        start = stranded[0]
        while start - 1 in headings:  # keep a run of headings together
            start -= 1
        breaks = frozenset(b for b in breaks if b < start or b > stranded[0]) | {start}

    first = document[0]
    first.draw_rect(
        pymupdf.Rect(0, 0, media.width, band_bottom),
        color=None,
        fill=(0x17 / 255, 0x4A / 255, 0x39 / 255),
        overlay=False,
    )
    first.insert_htmlbox(
        pymupdf.Rect(MARGIN_X, band_pad, media.width - MARGIN_X, band_pad + cover_rect_height),
        cover,
        css=COVER_CSS,
    )
    _header_footer(document, header or title)
    document.set_metadata(
        {
            "title": title,
            "author": f"Team {TEAM}",
            "subject": f"{PRODUCT} · {EVENT}",
            "creator": "Adept export script (PyMuPDF)",
        }
    )
    document.save(output, garbage=4, deflate=True)
    print(f"Exported {len(document)} pages to {output}")


def main() -> None:
    from template_pdf import render

    render(SOURCE, OUTPUT, "Adept Technical & Tools Declaration")


if __name__ == "__main__":
    main()
