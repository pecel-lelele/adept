"""Render a submission source in the organisers' template layout, and check its word limits.

Pages match the supplied finalist templates: 400 x 600 pt, 33 pt side margin, Charis SIL with
11 pt body, 22 pt section and 16.5 pt subsection headings. Prompts stay in black; answers are
Markdown blockquotes, tables and code blocks, shown in a darker blue.

Set SUBMISSION_FONT_DIR to a folder with CharisSIL-{Regular,Bold,Italic}.ttf and
NotoSansSymbols2-Regular.ttf for the exact fonts; otherwise a built-in serif is used.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

ANSWER_BLOCK = re.compile(
    r"<!-- answer:start (?P<name>\S+) limit=(?P<limit>\d+) -->(?P<body>.*?)<!-- answer:end \1 -->",
    re.DOTALL,
)
PAGE_WIDTH, PAGE_HEIGHT = 400, 600
MARGIN_X, MARGIN_Y = 33, 30
ANSWER = "#1b3a6b"


def word_count(text: str) -> int:
    """Count words as a reader would: Markdown markers and bullets are not words."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("•", " ")
    return len(text.split())


def word_limits(source: str) -> list[tuple[str, int, int]]:
    """Return (answer name, words, limit) for every limited answer in a source."""
    return [
        (m["name"], word_count(m["body"]), int(m["limit"])) for m in ANSWER_BLOCK.finditer(source)
    ]


def _inline(value: str) -> str:
    value = html.escape(value, quote=False)
    value = re.sub(r"\[([^\]]+)\]\((\S+?)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    return re.sub(r"([☐☑])", r'<span class="box">\1</span>', value)


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in rows]
    body = [row for row in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in row)]
    columns = len(body[0])
    tag_row = []
    for i, row in enumerate(body):
        tag = "th" if i == 0 else "td"
        width = f' style="width:{100 // columns}%"' if i == 0 else ""
        tag_row.append("<tr>" + "".join(f"<{tag}{width}>{_inline(c)}</{tag}>" for c in row) + "</tr>")
    return f'<table class="cols{columns}">' + "".join(tag_row) + "</table>"


def to_html(source: str) -> str:
    source = re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL)
    output: list[str] = []
    table: list[str] = []
    code: list[str] | None = None

    def flush_table() -> None:
        if table:
            output.append(_table(table))
            table.clear()

    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            flush_table()
            if code is None:
                code = []
            else:
                output.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code = None
        elif code is not None:
            code.append(raw)
        elif line.startswith("|"):
            table.append(line)
        else:
            flush_table()
            if line == "[[break]]":
                output.append('<div style="page-break-before: always"></div>')
            elif line == "[[diagram]]":
                output.append('<p class="fig"><img src="architecture.png"/></p>')
            elif line.startswith("### "):
                output.append(f"<h3>{_inline(line[4:])}</h3>")
            elif line.startswith("## "):
                output.append(f"<h2>{_inline(line[3:])}</h2>")
            elif line.startswith(">"):
                output.append(f'<p class="answer">{_inline(line[1:].strip())}</p>')
            elif line:
                output.append(f"<p>{_inline(line)}</p>")
    flush_table()
    return "<html><body>" + "\n".join(output) + "</body></html>"


def architecture_png() -> bytes:
    """Draw the system block diagram used in report section 3.1 and the declaration appendix."""
    import pymupdf

    page = (doc := pymupdf.open()).new_page(width=668, height=560)
    ink, blue, green = (0.11, 0.23, 0.42), (0.91, 0.94, 0.98), (0.9, 0.96, 0.92)

    def box(x: float, y: float, w: float, h: float, title: str, sub: str, fill=blue) -> None:
        rect = pymupdf.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=ink, fill=fill, width=1.4)
        for offset, text, font, size in ((8, title, "hebo", 17), (32, sub, "helv", 14)):
            clear = page.insert_textbox(
                rect + (4, offset, -4, -2), text, fontname=font, fontsize=size, color=ink, align=1
            )
            if clear < 0:
                raise ValueError(f"Diagram text does not fit: {text!r}")

    def arrow(start: tuple[float, float], end: tuple[float, float]) -> None:
        page.draw_line(start, end, color=ink, width=1.6)
        tip = pymupdf.Point(end)
        vector = tip - pymupdf.Point(start)
        unit = vector / abs(vector)
        side = pymupdf.Point(-unit.y, unit.x)
        wing_a, wing_b = tip - unit * 11 + side * 6, tip - unit * 11 - side * 6
        page.draw_polyline([wing_a, tip, wing_b], color=ink, fill=ink, closePath=True)

    box(6, 6, 208, 122, "Public sources", "arXiv, job feeds,\ncourse pages, DOSM,\nUN SDG", green)
    box(230, 6, 208, 122, "Refresh worker", "Daily GitHub trigger;\nruns in the deployed\napp, validates data", green)
    box(454, 6, 208, 122, "RunPod", "MiniLM research\nembeddings", green)
    arrow((214, 67), (230, 67))
    arrow((438, 67), (454, 67))
    box(6, 196, 116, 122, "Users", "Learner,\nmember,\nHR manager")
    box(142, 196, 150, 122, "Next.js", "Public interface\nin three\nlanguages")
    box(312, 196, 150, 122, "FastAPI", "Private API,\naccess checks")
    box(482, 196, 180, 122, "PostgreSQL", "Replit managed:\nprofiles, catalogue,\nsnapshots, plans")
    arrow((122, 257), (142, 257))
    arrow((292, 257), (312, 257))
    arrow((462, 257), (482, 257))
    arrow((400, 128), (560, 196))
    box(6, 400, 208, 154, "Skill suggestions", "Gemini Embedding 001\nsuggests a catalogue\nskill; the person\nconfirms it", green)
    box(230, 400, 208, 154, "Plan engine", "Deterministic score,\nskills gap, course plan,\nSDG contribution,\ntwo scenarios", green)
    box(454, 400, 208, 154, "Adi answer gate", "GLM-5.3 or Gemini\nselects answer IDs;\nthe server checks them\nand shows its own text", green)
    arrow((340, 318), (110, 400))
    arrow((370, 318), (334, 400))
    arrow((430, 318), (558, 400))
    png = page.get_pixmap(dpi=216).tobytes("png")
    doc.close()
    return png


def _css(has_fonts: bool) -> str:
    faces = (
        """
    @font-face { font-family: Charis; src: url(CharisSIL-Regular.ttf); }
    @font-face { font-family: Charis; font-weight: bold; src: url(CharisSIL-Bold.ttf); }
    @font-face { font-family: Charis; font-style: italic; src: url(CharisSIL-Italic.ttf); }
    @font-face { font-family: Sym; src: url(NotoSansSymbols2-Regular.ttf); }
    """
        if has_fonts
        else ""
    )
    family = "Charis, serif" if has_fonts else "serif"
    box = "Sym" if has_fonts else "serif"
    return f"""{faces}
    body {{ font-family: {family}; font-size: 11pt; line-height: 1.2; color: #000; }}
    h2 {{ font-size: 22pt; font-weight: bold; line-height: 1.2; margin: 22pt 0 12pt 0; }}
    h3 {{ font-size: 16.5pt; font-weight: bold; line-height: 1.2; margin: 16pt 0 8pt 0; }}
    p {{ margin: 0 0 9pt 0; }}
    p.answer {{ color: {ANSWER}; }}
    p.fig {{ margin: 6pt 0 9pt 0; }}
    img {{ width: 334pt; }}
    .box {{ font-family: {box}; }}
    a {{ color: {ANSWER}; text-decoration: none; }}
    table {{ width: 100%; border-collapse: collapse; margin: 3pt 0 10pt 0; }}
    table.cols3 th, table.cols3 td {{ font-size: 8.5pt; }}
    table.cols4 th, table.cols4 td {{ font-size: 8pt; }}
    table.cols5 th, table.cols5 td {{ font-size: 7.5pt; }}
    th {{ font-weight: bold; text-align: left; padding: 2pt 3pt 3pt 0; border-bottom: 0.6pt solid #000; }}
    td {{ color: {ANSWER}; padding: 3pt 3pt 3pt 0; border-bottom: 0.3pt solid #b8bcc4; line-height: 1.15; }}
    pre {{ font-family: monospace; font-size: 7.6pt; line-height: 1.2; color: {ANSWER}; margin: 0 0 9pt 0; }}
    """


def render(source_path: Path, output_path: Path, title: str) -> None:
    import pymupdf

    source = source_path.read_text("utf-8")
    font_dir = os.environ.get("SUBMISSION_FONT_DIR", "")
    has_fonts = bool(font_dir) and (Path(font_dir) / "CharisSIL-Regular.ttf").exists()
    archive = pymupdf.Archive()
    if has_fonts:
        archive.add(font_dir)
    archive.add(architecture_png(), "architecture.png")
    story = pymupdf.Story(to_html(source), user_css=_css(has_fonts), archive=archive)
    media = pymupdf.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
    body = pymupdf.Rect(MARGIN_X, MARGIN_Y, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - MARGIN_Y)
    document = story.write_with_links(lambda _number, _filled: (media, body, None))
    document.set_metadata({"title": title, "author": "Team Pecel Lele", "subject": "SDC Hackathon 2026"})
    document.save(output_path, garbage=4, deflate=True)
    over = [item for item in word_limits(source) if item[1] > item[2]]
    print(f"Exported {len(document)} pages to {output_path}; answers over limit: {over or 'none'}")
