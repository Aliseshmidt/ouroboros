#!/usr/bin/env python3
"""Render the hackathon's compact Markdown reports as polished PDFs.

The renderer intentionally supports the small Markdown subset used by the
submission pack: headings, paragraphs, bullets, fenced code, and pipe tables.
It has no network or browser dependency and embeds a Cyrillic-capable font.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FONT_CANDIDATES = (
    (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Italic.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
    ),
)


def _register_fonts() -> tuple[str, str, str]:
    for regular, bold, italic in FONT_CANDIDATES:
        if regular.exists() and bold.exists() and italic.exists():
            pdfmetrics.registerFont(TTFont("HackRegular", str(regular)))
            pdfmetrics.registerFont(TTFont("HackBold", str(bold)))
            pdfmetrics.registerFont(TTFont("HackItalic", str(italic)))
            pdfmetrics.registerFontFamily(
                "HackRegular",
                normal="HackRegular",
                bold="HackBold",
                italic="HackItalic",
                boldItalic="HackBold",
            )
            return "HackRegular", "HackBold", "HackItalic"
    raise RuntimeError("No Cyrillic-capable font found; install Arial or DejaVu Sans")


def _styles() -> dict[str, ParagraphStyle]:
    regular, bold, italic = _register_fonts()
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName=bold,
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#162033"),
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName=bold,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#162033"),
            spaceBefore=5 * mm,
            spaceAfter=2.5 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=bold,
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#9E2636"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=regular,
            fontSize=9.6,
            leading=14,
            textColor=colors.HexColor("#263348"),
            spaceAfter=2.4 * mm,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=regular,
            fontSize=9.3,
            leading=13,
            leftIndent=2 * mm,
            textColor=colors.HexColor("#263348"),
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=regular,
            fontSize=7.8,
            leading=10.5,
            textColor=colors.HexColor("#E8EDF5"),
            backColor=colors.HexColor("#162033"),
            borderPadding=8,
            spaceBefore=2 * mm,
            spaceAfter=3 * mm,
        ),
        "table": ParagraphStyle(
            "TableCell",
            fontName=regular,
            fontSize=7.7,
            leading=9.5,
            textColor=colors.HexColor("#263348"),
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName=bold,
            fontSize=7.7,
            leading=9.5,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName=regular,
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#718096"),
            alignment=TA_CENTER,
        ),
        "italic": ParagraphStyle(
            "Italic",
            fontName=italic,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#526178"),
        ),
    }


def _inline(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r"<font name='HackRegular' color='#9E2636'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
    escaped = re.sub(r"\[([^]]+)]\(([^)]+)\)", r"<u>\1</u>", escaped)
    return escaped


def _table(lines: list[str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in rows[1]):
        rows.pop(1)
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    rendered = []
    for row_index, row in enumerate(normalized):
        style = styles["table_header"] if row_index == 0 else styles["table"]
        rendered.append([Paragraph(_inline(cell), style) for cell in row])
    table = Table(rendered, colWidths=[width / columns] * columns, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#162033")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F7FA")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _blocks(markdown: str, styles: dict[str, ParagraphStyle], width: float) -> Iterable[object]:
    lines = markdown.splitlines()
    index = 0
    first_heading = True
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            yield Spacer(1, 1.5 * mm)
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            index += 1
            body: list[str] = []
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            label = f"[{language}]\n" if language else ""
            yield Preformatted(label + "\n".join(body), styles["code"])
            continue
        if line.startswith("|") and "|" in line[1:]:
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            yield Spacer(1, 1 * mm)
            yield _table(table_lines, styles, width)
            yield Spacer(1, 3 * mm)
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            style_name = "title" if first_heading and level == 1 else ("h1" if level == 1 else "h2")
            first_heading = False
            yield Paragraph(_inline(heading.group(2)), styles[style_name])
            index += 1
            continue
        if re.match(r"^[-*]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^[-*]\s+", lines[index].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[index].strip())
                items.append(ListItem(Paragraph(_inline(item), styles["bullet"]), leftIndent=3 * mm))
                index += 1
            yield ListFlowable(
                items, bulletType="bullet", start="circle", leftIndent=5 * mm, bulletFontName="HackRegular"
            )
            yield Spacer(1, 2 * mm)
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("#", "```", "|", "- ", "* ")):
                break
            paragraph.append(candidate)
            index += 1
        text = " ".join(paragraph)
        style = styles["italic"] if text.startswith(">") else styles["body"]
        yield Paragraph(_inline(text.lstrip("> ")), style)


def render(source: Path, destination: Path) -> None:
    styles = _styles()
    destination.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    margin_x = 17 * mm
    margin_top = 18 * mm
    margin_bottom = 16 * mm
    content_width = page_width - (2 * margin_x)

    def page(canvas, document) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(margin_x, 12 * mm, page_width - margin_x, 12 * mm)
        footer = Paragraph(f"Ouroboros · Sber AI Hack · {html.escape(source.stem)} · {document.page}", styles["footer"])
        footer.wrapOn(canvas, content_width, 8 * mm)
        footer.drawOn(canvas, margin_x, 5 * mm)
        canvas.restoreState()

    frame = Frame(
        margin_x,
        margin_bottom,
        content_width,
        page_height - margin_top - margin_bottom,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    document = BaseDocTemplate(
        str(destination),
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        title=source.stem,
        author="Ouroboros / Sber AI Hack",
        subject="Personal Micro-Automation Agent",
    )
    document.addPageTemplates([PageTemplate(id="submission", frames=[frame], onPage=page)])
    story = list(_blocks(source.read_text(encoding="utf-8"), styles, content_width))
    document.build(
        [
            KeepTogether(item) if isinstance(item, Paragraph) and item.style.name in {"H1", "H2"} else item
            for item in story
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "output" / "pdf")
    args = parser.parse_args()
    for source in args.sources:
        destination = args.output_dir / f"{source.stem}.pdf"
        render(source.resolve(), destination.resolve())
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
