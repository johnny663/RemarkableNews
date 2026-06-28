import io
import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
)

from models import Article

# reMarkable Paper Pro Move screen is ~954 x 1696 px (a small ~7.3" panel).
# Match that aspect ratio so the page fills the screen with no wasted margins
# and text stays large enough to read without zooming.
PAGE_SIZE = (4.7 * inch, 8.35 * inch)
MARGIN = 0.4 * inch

GRAY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#cccccc")
LINK = colors.HexColor("#1a3d5c")  # dark blue — reads as a clear gray on e-ink


def _styles() -> dict:
    return {
        "masthead": ParagraphStyle("masthead", fontName="Times-Bold", fontSize=22,
                                   leading=26, spaceAfter=2, alignment=TA_LEFT),
        "dateline": ParagraphStyle("dateline", fontName="Helvetica", fontSize=9,
                                   textColor=GRAY, spaceAfter=8),
        "toc_head": ParagraphStyle("toc_head", fontName="Helvetica-Bold", fontSize=12,
                                   spaceBefore=10, spaceAfter=6),
        "toc_title": ParagraphStyle("toc_title", fontName="Helvetica-Bold", fontSize=11,
                                    leading=14, spaceBefore=8, spaceAfter=1),
        "toc_meta": ParagraphStyle("toc_meta", fontName="Helvetica", fontSize=7.5,
                                   textColor=GRAY, spaceAfter=2),
        "toc_teaser": ParagraphStyle("toc_teaser", fontName="Helvetica", fontSize=8.5,
                                     leading=11, textColor=colors.HexColor("#333333"),
                                     spaceAfter=2),
        "toc_link": ParagraphStyle("toc_link", fontName="Helvetica-Oblique", fontSize=8,
                                   textColor=LINK, spaceAfter=4),
        "section_tag": ParagraphStyle("section_tag", fontName="Helvetica-Bold", fontSize=7,
                                      textColor=GRAY, spaceAfter=3),
        "article_title": ParagraphStyle("article_title", fontName="Times-Bold", fontSize=16,
                                        leading=19, spaceAfter=3),
        "byline": ParagraphStyle("byline", fontName="Helvetica", fontSize=8,
                                 textColor=GRAY, spaceAfter=9),
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11,
                               leading=15, spaceAfter=8),
        "summary_note": ParagraphStyle("summary_note", fontName="Helvetica-Oblique", fontSize=7.5,
                                       textColor=GRAY, spaceBefore=8),
        "url": ParagraphStyle("url", fontName="Helvetica", fontSize=7,
                              textColor=GRAY, spaceBefore=5),
    }


def _teaser(text: str, limit: int = 200) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= limit:
        return flat
    return flat[:limit].rsplit(" ", 1)[0] + "…"


def _body_paragraphs(text: str, style) -> list:
    chunks = [c.strip() for c in text.replace("\r", "").split("\n") if c.strip()]
    if not chunks and text.strip():
        chunks = [text.strip()]
    return [Paragraph(escape(c), style) for c in chunks]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_SIZE[0] / 2, 0.25 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def build_pdf(articles: list[Article], date_str: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=PAGE_SIZE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=0.45 * inch,
        title=f"Daily News · {date_str}",
    )
    s = _styles()
    story = []

    # --- Cover + clickable summary list ---
    story.append(Paragraph("Daily News Digest", s["masthead"]))
    story.append(Paragraph(date_str, s["dateline"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceAfter=4))
    story.append(Paragraph("In this issue", s["toc_head"]))

    for i, article in enumerate(articles):
        anchor = f"article{i}"
        # Title links to the article's page later in the document
        title = f'<a href="#{anchor}" color="#1a3d5c">{i + 1}. {escape(article.title)}</a>'
        story.append(Paragraph(title, s["toc_title"]))

        meta = " · ".join(b for b in (article.section, article.source) if b)
        if meta:
            story.append(Paragraph(escape(meta), s["toc_meta"]))

        if article.body.strip():
            story.append(Paragraph(escape(_teaser(article.body)), s["toc_teaser"]))

        verb = "Read full article →" if article.is_full else "Open summary →"
        story.append(Paragraph(f'<a href="#{anchor}" color="#1a3d5c">{verb}</a>', s["toc_link"]))

    # --- One article per page, each a link destination ---
    for i, article in enumerate(articles):
        anchor = f"article{i}"
        story.append(PageBreak())

        # Anchor (link destination) sits in the first flowable on the page
        tag = escape(article.section.upper()) if article.section else ""
        story.append(Paragraph(f'<a name="{anchor}"/>{tag}', s["section_tag"]))
        story.append(Paragraph(escape(article.title), s["article_title"]))

        meta_bits = [b for b in (article.byline, article.source, article.published_date) if b]
        if meta_bits:
            story.append(Paragraph(escape(" · ".join(meta_bits)), s["byline"]))

        story.extend(_body_paragraphs(article.body, s["body"]))

        if not article.is_full:
            story.append(Paragraph(
                "Summary only — open the link for the complete article.",
                s["summary_note"]))
        if article.url:
            story.append(Paragraph(escape(article.url), s["url"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
