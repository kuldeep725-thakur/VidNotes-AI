"""Builds a printable PDF of the study material with ReportLab."""

import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.video import Language, LanguageContent, VideoDetail
from app.utils.time_format import format_timestamp

ACCENT = colors.HexColor("#6d4aff")
INK = colors.HexColor("#1b1b22")
MUTED = colors.HexColor("#5d5d6b")
SOFT_FILL = colors.HexColor("#f3f0ff")

LANGUAGE_LABELS = {"en": "English", "hinglish": "Hinglish"}

# Unicode TrueType fonts render symbols such as arrows that Helvetica cannot.
_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ),
    ("/Library/Fonts/Arial Unicode.ttf",) * 3,
]


@lru_cache
def _fonts() -> tuple[str, str, str, bool]:
    """Return (regular, bold, italic, is_unicode) font names."""
    for regular, bold, italic in _FONT_CANDIDATES:
        if all(Path(path).is_file() for path in (regular, bold, italic)):
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            pdfmetrics.registerFont(TTFont("Body-Italic", italic))
            pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic")
            return "Body", "Body-Bold", "Body-Italic", True
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", False


def _markup(text: str) -> str:
    """Escape text for ReportLab and turn **bold** into real bold."""
    if not _fonts()[3]:
        # Built-in fonts only support Latin-1 characters.
        text = text.replace("→", "->").replace("←", "<-").replace("–", "-").replace("—", "-")
        text = text.encode("latin-1", "replace").decode("latin-1")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(text))


def _styles() -> dict[str, ParagraphStyle]:
    regular, bold, italic, _ = _fonts()
    base = ParagraphStyle("base", fontName=regular, fontSize=10.5, leading=15.5, textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("title", base, fontName=bold, fontSize=20, leading=25, spaceAfter=4),
        "meta": ParagraphStyle("meta", base, fontSize=9, leading=13, textColor=MUTED),
        "h1": ParagraphStyle("h1", base, fontName=bold, fontSize=15, leading=20, textColor=ACCENT,
                             spaceBefore=14, spaceAfter=8),
        "h2": ParagraphStyle("h2", base, fontName=bold, fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", base, fontName=bold, fontSize=11, leading=15, spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", base, spaceAfter=6),
        "note": ParagraphStyle("note", base, fontName=italic, textColor=MUTED, spaceAfter=6),
        "boxed": ParagraphStyle("boxed", base, fontSize=10),
    }


def _bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(_markup(item), style), leftIndent=12) for item in items],
        bulletType="bullet",
        bulletFontSize=7,
        bulletColor=ACCENT,
        leftIndent=12,
        spaceAfter=6,
    )


def _boxed(label: str, text: str, style: ParagraphStyle) -> Table:
    table = Table([[Paragraph(f"<b>{label}:</b> {_markup(text)}", style)]], colWidths=["100%"])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT_FILL),
            ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    return table


def build_pdf(video: VideoDetail, language: Language) -> bytes:
    content: LanguageContent = video.content[language]
    styles = _styles()
    story = [Paragraph(_markup(video.title), styles["title"])]

    meta = [video.channel_name, LANGUAGE_LABELS[language] + " notes"]
    if video.duration_seconds:
        meta.insert(1, f"Duration {format_timestamp(video.duration_seconds)}")
    story.append(Paragraph(_markup(" · ".join(part for part in meta if part)), styles["meta"]))
    url = escape(video.url)
    story.append(Paragraph(f'<link href="{url}" color="#6d4aff">{url}</link>', styles["meta"]))

    summary = content.summary
    story.append(Paragraph("Summary", styles["h1"]))
    for paragraph in summary.overview.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(_markup(paragraph.strip()), styles["body"]))
    for topic in summary.topics:
        story.append(KeepTogether([
            Paragraph(_markup(topic.title), styles["h3"]),
            Paragraph(_markup(topic.explanation), styles["body"]),
        ]))

    story.append(Paragraph("Important Concepts", styles["h1"]))
    for concept in summary.key_concepts:
        story.append(Paragraph(f"<b>{_markup(concept.term)}</b> — {_markup(concept.explanation)}", styles["body"]))

    story.append(Paragraph("Key Takeaways", styles["h1"]))
    story.append(_bullets(summary.key_takeaways, styles["body"]))

    story.append(PageBreak())
    story.append(Paragraph("Study Notes", styles["h1"]))
    for section in content.notes.sections:
        story.append(Paragraph(_markup(section.heading), styles["h2"]))
        if section.introduction:
            story.append(Paragraph(_markup(section.introduction), styles["body"]))
        for sub in section.subsections:
            story.append(Paragraph(_markup(sub.heading), styles["h3"]))
            if sub.definition:
                story += [_boxed("Definition", sub.definition, styles["boxed"]), Spacer(1, 5)]
            if sub.points:
                story.append(_bullets(sub.points, styles["body"]))
            if sub.example:
                story.append(Paragraph(f"<b>Example:</b> {_markup(sub.example)}", styles["note"]))

    if content.timestamps:
        story.append(Paragraph("Important Timestamps", styles["h1"]))
        for stamp in content.timestamps:
            link = f"{video.url}&amp;t={stamp.seconds}s"
            story.append(Paragraph(
                f'<link href="{link}" color="#6d4aff"><b>{format_timestamp(stamp.seconds)}</b></link>'
                f"  {_markup(stamp.title)} — {_markup(stamp.description)}",
                styles["body"],
            ))

    story.append(PageBreak())
    story.append(Paragraph("Questions &amp; Answers", styles["h1"]))
    for number, pair in enumerate(content.qa, start=1):
        story.append(KeepTogether([
            Paragraph(f"<b>Q{number}. {_markup(pair.question)}</b>", styles["body"]),
            Paragraph(_markup(pair.answer), styles["body"]),
            Spacer(1, 4),
        ]))

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=video.title,
        author="VidNotes AI",
    )
    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()


def _draw_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont(_fonts()[0], 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 10 * mm, "VidNotes AI — Turn videos into knowledge.")
    canvas.drawRightString(A4[0] - document.rightMargin, 10 * mm, f"Page {document.page}")
    canvas.restoreState()
