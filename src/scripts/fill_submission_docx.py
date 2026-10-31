"""Fill the organisers' Word templates from the tracked Markdown sources.

The templates in submission/templates stay as supplied: every heading, prompt and table is kept,
and only answer cells, extra table rows and tick boxes change. Answers in the sources are
Markdown blockquotes, tables and code blocks, taken in order, one group per template field.

python-docx is used only here, not by the application:
    uv run --with python-docx python src/scripts/fill_submission_docx.py
Open the result in Word to sign it and save the PDF the organisers ask for.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "submission" / "templates"
ANSWER_BLOCK = re.compile(
    r"<!-- answer:start (?P<name>\S+) limit=(?P<limit>\d+) -->(?P<body>.*?)<!-- answer:end \1 -->",
    re.DOTALL,
)
DOCUMENTS = {
    "final": (
        ROOT / "docs/submission/submission-final-report.md",
        TEMPLATES / "SDC Hackathon Submission Template (Finalists).docx",
        ROOT / "submission/SDC2026_Pecel-Lele_Final.docx",
    ),
    "declaration": (
        ROOT / "docs/submission/submission-technical-declaration.md",
        TEMPLATES / "SDC Hackathon Tech. Tools Declaration Template (Finalist).docx",
        ROOT / "submission/SDC2026_Pecel-Lele_TechDeclaration.docx",
    ),
}
FONT = "Times New Roman"


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


def parse_groups(source: str) -> tuple[list[list[tuple[str, object]]], list[str]]:
    """Split a source into ordered answer groups and its tick-box lines.

    A group holds ("text", line), ("code", lines), ("table", rows) or ("diagram", None) items.
    Any plain prompt line ends the current group.
    """
    source = re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL)
    groups: list[list[tuple[str, object]]] = []
    ticks: list[str] = []
    current: list[tuple[str, object]] = []
    table: list[list[str]] = []
    code: list[str] | None = None

    def close_table() -> None:
        if table:
            current.append(("table", list(table)))
            table.clear()

    def close_group() -> None:
        nonlocal current
        close_table()
        if current:
            groups.append(current)
            current = []

    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            if code is None:
                close_table()
                code = []
            else:
                current.append(("code", code))
                code = None
        elif code is not None:
            code.append(raw)
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                table.append(cells)
        elif line == "[[diagram]]":
            close_table()
            current.append(("diagram", None))
        elif line.startswith(">"):
            close_table()
            current.append(("text", line[1:].strip()))
        elif line and line != "[[break]]":
            close_group()
            if line[0] in "☐☑":
                ticks.append(line)
    close_group()
    return groups, ticks


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
    box(
        230,
        6,
        208,
        122,
        "Refresh worker",
        "Daily GitHub trigger;\nruns in the deployed\napp, validates data",
        green,
    )
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
    box(
        6,
        400,
        208,
        154,
        "Skill suggestions",
        "Gemini Embedding 001\nsuggests a catalogue\nskill; the person\nconfirms it",
        green,
    )
    box(
        230,
        400,
        208,
        154,
        "Plan engine",
        "Deterministic score,\nskills gap, course plan,\nSDG contribution,\ntwo scenarios",
        green,
    )
    box(
        454,
        400,
        208,
        154,
        "Adi answer gate",
        "GLM-5.3 or Gemini\nselects answer IDs;\nthe server checks them\nand shows its own text",
        green,
    )
    arrow((340, 318), (110, 400))
    arrow((370, 318), (334, 400))
    arrow((430, 318), (558, 400))
    png = page.get_pixmap(dpi=216).tobytes("png")
    doc.close()
    return png


def _add_runs(paragraph, text: str, size: float) -> None:
    from docx.shared import Pt

    text = re.sub(r"\[([^\]]+)\]\(\S+?\)", r"\1", text)
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            run = paragraph.add_run(part)
            run.bold = i % 2 == 1
            run.font.name = FONT
            run.font.size = Pt(size)


def _write_cell(cell, items: list[tuple[str, object]], size: float = 11) -> None:
    """Replace a cell's blank paragraphs with an answer, keeping the cell's own formatting."""
    from docx.shared import Inches, Pt

    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    first = cell.paragraphs[0]
    for child in list(first._p):
        if not child.tag.endswith("}pPr"):
            first._p.remove(child)
    used = False

    def next_paragraph():
        nonlocal used
        if used:
            return cell.add_paragraph()
        used = True
        return first

    for kind, value in items:
        paragraph = next_paragraph()
        paragraph.paragraph_format.space_after = Pt(5)
        if kind == "text":
            _add_runs(paragraph, str(value), size)
        elif kind == "diagram":
            paragraph.add_run().add_picture(_diagram_file(), width=Inches(5.9))
        elif kind == "code":
            for i, line in enumerate(value):
                run = paragraph.add_run(line)
                run.font.name = "Courier New"
                run.font.size = Pt(8.5)
                if i < len(value) - 1:
                    run.add_break()


def _diagram_file():
    import io

    return io.BytesIO(architecture_png())


def _fill_table(table, rows: list[list[str]], size: float) -> None:
    """Fill data rows under the template's header row, adding or removing rows as needed."""
    body = rows[1:]
    while len(table.rows) - 1 < len(body):
        table._tbl.append(copy.deepcopy(table.rows[-1]._tr))
    while len(table.rows) - 1 > len(body):
        table._tbl.remove(table.rows[-1]._tr)
    for row, values in zip(table.rows[1:], body, strict=True):
        for cell, value in zip(row.cells, values, strict=True):
            _write_cell(cell, [("text", value)], size)


def _strip_padding(document) -> None:
    """Remove the runs of blank spacer paragraphs that only padded the empty template."""
    previous_blank = False
    for element in list(document.element.body):
        if not element.tag.endswith("}p"):
            previous_blank = False
            continue
        blank = not "".join(element.itertext()).strip() and "<w:drawing" not in element.xml
        if blank and (previous_blank or element.xpath("./w:pPr/w:pStyle")):
            if not element.xpath(".//w:sectPr"):
                document.element.body.remove(element)
                continue
        previous_blank = blank


def _tick(document, ticks: list[str]) -> None:
    """Apply the source's tick boxes, in order, to the template's unticked boxes."""
    marks = iter(mark for line in ticks for mark in re.findall(r"[☐☑]", line))
    for text_node in document.element.body.iter(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
    ):
        if text_node.text and "☐" in text_node.text:
            text_node.text = re.sub("☐", lambda _m: next(marks), text_node.text)
    if next(marks, None) is not None:
        raise ValueError("The source has more tick boxes than the template")


def _note_after(table, text: str) -> None:
    from docx.oxml import OxmlElement
    from docx.shared import Pt
    from docx.text.paragraph import Paragraph

    element = OxmlElement("w:p")
    table._tbl.addnext(element)
    paragraph = Paragraph(element, table._parent)
    paragraph.paragraph_format.space_before = Pt(6)
    _add_runs(paragraph, text, 11)


def _fill_group(table, group: list[tuple[str, object]], size: float) -> None:
    rows = next(value for kind, value in group if kind == "table")
    _fill_table(table, rows, size)
    for kind, value in reversed(group):
        if kind == "text":
            _note_after(table, str(value))


def fill_final(document, groups: list) -> None:
    tables = document.tables
    for index, group in enumerate(groups[:6]):
        _write_cell(tables[index + 1].rows[0].cells[1], group)
    _write_cell(tables[7].rows[0].cells[0], groups[6])
    _write_cell(tables[8].rows[0].cells[0], groups[7])
    _write_cell(tables[9].rows[0].cells[0], groups[8])
    for row, group in zip(tables[10].rows[1:], groups[9:13], strict=True):
        _write_cell(row.cells[1], group, 10.5)
    _write_cell(tables[11].rows[0].cells[0], groups[13])
    _write_cell(tables[12].rows[0].cells[0], groups[14])
    _write_after_prompt(document, "If yes, briefly describe what was pre-existing", groups[15])
    _fill_group(tables[18], groups[16], 10)
    _write_after_prompt(document, "If yes, please describe the nature of the agreement", groups[17])


def _write_after_prompt(document, prompt: str, group: list[tuple[str, object]]) -> None:
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    anchor = next(p for p in document.paragraphs if p.text.startswith(prompt))
    element = OxmlElement("w:p")
    anchor._p.addnext(element)
    _add_runs(Paragraph(element, anchor._parent), str(group[0][1]), 11)


def fill_declaration(document, groups: list) -> None:
    from docx.shared import Inches

    tables = document.tables
    for row, group in zip(tables[1].rows, groups[:7], strict=True):
        _write_cell(row.cells[1], group)
    _write_cell(tables[2].rows[0].cells[0], groups[7])
    for table, group, size in (
        (tables[3], groups[8], 10),
        (tables[4], groups[9], 10),
        (tables[5], groups[10], 10),
        (tables[6], groups[11], 9.5),
        (tables[7], groups[12], 9),
        (tables[8], groups[13], 10),
    ):
        _fill_group(table, group, size)
    _write_cell(tables[9].rows[0].cells[0], groups[14])
    _fill_group(tables[10], groups[15], 10)
    _write_cell(tables[11].rows[0].cells[0], groups[16])
    _write_cell(tables[12].rows[0].cells[0], groups[17])
    _write_cell(tables[13].rows[0].cells[0], groups[18])
    document.add_page_break()
    document.add_heading("Appendix: System Block Diagram", level=1)
    document.add_paragraph().add_run().add_picture(_diagram_file(), width=Inches(6.4))


def fill(name: str) -> None:
    from docx import Document

    source_path, template, output = DOCUMENTS[name]
    source = source_path.read_text("utf-8")
    over = [item for item in word_limits(source) if item[1] > item[2]]
    if over:
        raise SystemExit(f"Answers over the word limit: {over}")
    groups, ticks = parse_groups(source)
    document = Document(str(template))
    if name == "final":
        fill_final(document, groups)
        # Section 6 boxes are empty cells in this template, not box characters.
        _tick(document, ticks[5:])
        # Each section 6 box is a small nested table in this template; a tick goes inside it.
        for table, line in zip(document.tables[13:18], ticks[:5], strict=True):
            box = table.rows[0].cells[0].tables[0].rows[0].cells[0]
            if line[0] == "☑":
                _add_runs(box.paragraphs[0], "✓", 8)
    else:
        fill_declaration(document, groups)
        _tick(document, ticks)
    _strip_padding(document)
    document.save(str(output))
    print(f"Wrote {output.name}; {len(groups)} answers; word limits respected")


if __name__ == "__main__":
    for key in sys.argv[1:] or list(DOCUMENTS):
        fill(key)
