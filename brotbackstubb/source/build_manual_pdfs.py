"""Build the two downloadable manuals from the maintained Markdown sources."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("ManualArial", str(FONT_DIR / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ManualArial-Bold", str(FONT_DIR / "Arial Bold.ttf")))
pdfmetrics.registerFontFamily("ManualArial", normal="ManualArial", bold="ManualArial-Bold")

INK = colors.HexColor("#29231e")
ACCENT = colors.HexColor("#985020")
MUTED = colors.HexColor("#756b61")

STYLES = {
    "title": ParagraphStyle("title", fontName="ManualArial-Bold", fontSize=21, leading=27, textColor=ACCENT, spaceAfter=17),
    "h2": ParagraphStyle("h2", fontName="ManualArial-Bold", fontSize=14.5, leading=19, textColor=ACCENT, spaceBefore=20, spaceAfter=8, keepWithNext=True),
    "h3": ParagraphStyle("h3", fontName="ManualArial-Bold", fontSize=11.4, leading=15, textColor=INK, spaceBefore=13, spaceAfter=5, keepWithNext=True),
    "h4": ParagraphStyle("h4", fontName="ManualArial-Bold", fontSize=10, leading=13, textColor=ACCENT, spaceBefore=9, spaceAfter=4, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="ManualArial", fontSize=9, leading=13, textColor=INK, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName="ManualArial", fontSize=9, leading=13, textColor=INK, leftIndent=13, firstLineIndent=-9, spaceAfter=3.5),
    "table": ParagraphStyle("table", fontName="ManualArial", fontSize=8.1, leading=11, textColor=INK),
    "footer": ParagraphStyle("footer", fontName="ManualArial", fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER),
}


def inline(value: str) -> str:
    value = html.escape(value.strip().replace("⌘", "Cmd+"))
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r"<font color='#985020'>\1</font>", value)
    return value


def add_table(rows: list[str], story: list) -> None:
    parsed = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows]
    parsed = [row for row in parsed if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in row)]
    if not parsed:
        return
    count = max(len(row) for row in parsed)
    data = [
        [Paragraph(inline(row[col]) if col < len(row) else "", STYLES["table"]) for col in range(count)]
        for row in parsed
    ]
    width = 487
    widths = [width * 0.28, width * 0.72] if count == 2 else [width / count] * count
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eee5da")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbbdab")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([Spacer(1, 5), table, Spacer(1, 8)])


def build(source_name: str, output_name: str) -> None:
    source_path = ROOT / "source" / source_name
    lines = source_path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        closing = lines.index("---", 1)
        lines = lines[closing + 1:]
    story = []
    paragraph: list[str] = []
    table_rows: list[str] = []

    def add_image(path: Path, caption: str) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        width, height = ImageReader(str(path)).getSize()
        scale = min(487 / width, 215 / height)
        story.append(Spacer(1, 5))
        story.append(Image(str(path), width=width * scale, height=height * scale, hAlign="CENTER"))
        story.append(Paragraph(inline(caption), STYLES["footer"]))
        story.append(Spacer(1, 8))

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), STYLES["body"]))
            paragraph.clear()
        if table_rows:
            add_table(table_rows, story)
            table_rows.clear()

    for line in lines:
        clean = line.strip()
        if not clean:
            flush()
            continue
        if clean.startswith("|"):
            if paragraph:
                flush()
            table_rows.append(clean)
            continue
        if table_rows:
            flush()
        heading = re.match(r"^(#{1,4})\s+(.+)$", clean)
        if heading:
            flush()
            level = len(heading.group(1))
            story.append(Paragraph(inline(heading.group(2)), STYLES[{1: "title", 2: "h2", 3: "h3", 4: "h4"}[level]]))
            if level == 2 and heading.group(2) in {"Überblick", "Overview"}:
                language = "de" if source_name.endswith("de.md") else "en"
                add_image(ROOT / language / "images" / "overview.png", "BrotBackstubb")
            continue
        illustration = re.match(r"^!\[(.*?)\]\((.*?)\)$", clean)
        if illustration:
            flush()
            add_image((source_path.parent / illustration.group(2)).resolve(), illustration.group(1))
            continue
        bullet = re.match(r"^(?:[-*]|\d+\.)\s+(.+)$", clean)
        if bullet:
            flush()
            story.append(Paragraph("• " + inline(bullet.group(1)), STYLES["bullet"]))
            continue
        if clean.startswith(">"):
            flush()
            story.append(Paragraph(inline(clean.lstrip("> ")), STYLES["bullet"]))
            continue
        paragraph.append(clean)
    flush()

    target = ROOT / "downloads" / output_name
    document = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=54, rightMargin=54, topMargin=51, bottomMargin=51,
                                 title=next((line.lstrip("# ") for line in lines if line.startswith("# ")), "BrotBackstubb Manual"),
                                 author="BrotBackstubb")

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d4c6b7"))
        canvas.line(54, 38, A4[0] - 54, 38)
        canvas.setFont("ManualArial", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(54, 26, "BrotBackstubb · Mac & iPad")
        canvas.drawRightString(A4[0] - 54, 26, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build("manual-de.md", "BrotBackstubb-Benutzerhandbuch-DE.pdf")
    build("manual-en.md", "BrotBackstubb-User-Manual-EN.pdf")
