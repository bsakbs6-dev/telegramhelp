import os
import re
import html
import uuid
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import settings

logger = logging.getLogger(__name__)

# Search for available Cyrillic TrueType fonts across Windows and Linux
REGULAR_FONT_CANDIDATES = [
    # Linux paths (Debian/Ubuntu/Docker)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    # Windows paths
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]

BOLD_FONT_CANDIDATES = [
    # Linux paths
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    # Windows paths
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]

FONT_REGULAR_NAME = "Helvetica"
FONT_BOLD_NAME = "Helvetica-Bold"

for path in REGULAR_FONT_CANDIDATES:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont("CustomSans", path))
            FONT_REGULAR_NAME = "CustomSans"
            break
        except Exception as e:
            logger.warning(f"Could not load regular font {path}: {e}")

for path in BOLD_FONT_CANDIDATES:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont("CustomSans-Bold", path))
            FONT_BOLD_NAME = "CustomSans-Bold"
            break
        except Exception as e:
            logger.warning(f"Could not load bold font {path}: {e}")

if FONT_REGULAR_NAME == "CustomSans" and FONT_BOLD_NAME == "Helvetica-Bold":
    FONT_BOLD_NAME = "CustomSans"


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and display total page count.
    Adds a neat header and footer on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages: int):
        self.saveState()
        self.setFont(FONT_REGULAR_NAME, 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Top Header (Only on page 2 and onwards)
        if self._pageNumber > 1:
            self.drawString(54, 800, "Конспект лекций • Распознано и структурировано с помощью ИИ")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 794, 541, 794)

        # Bottom Footer
        page_str = f"Страница {self._pageNumber} из {total_pages}"
        self.drawRightString(541, 35, page_str)
        
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.drawString(54, 35, f"Сгенерировано ботом • {date_str}")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 541, 46)

        self.restoreState()


class PDFService:
    def __init__(self):
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        self.styles = self._setup_styles()

    def _setup_styles(self):
        return {
            "DocTitle": ParagraphStyle(
                "DocTitle",
                fontName=FONT_BOLD_NAME,
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=12,
                spaceBefore=6,
            ),
            "Heading1": ParagraphStyle(
                "Heading1",
                fontName=FONT_BOLD_NAME,
                fontSize=15,
                leading=19,
                textColor=colors.HexColor("#1E3A8A"),
                spaceBefore=14,
                spaceAfter=6,
                keepWithNext=True,
            ),
            "Heading2": ParagraphStyle(
                "Heading2",
                fontName=FONT_BOLD_NAME,
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#2563EB"),
                spaceBefore=10,
                spaceAfter=4,
                keepWithNext=True,
            ),
            "Heading3": ParagraphStyle(
                "Heading3",
                fontName=FONT_BOLD_NAME,
                fontSize=10.5,
                leading=14,
                textColor=colors.HexColor("#334155"),
                spaceBefore=8,
                spaceAfter=3,
                keepWithNext=True,
            ),
            "Body": ParagraphStyle(
                "Body",
                fontName=FONT_REGULAR_NAME,
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#1E293B"),
                spaceAfter=6,
            ),
            "Bullet": ParagraphStyle(
                "Bullet",
                fontName=FONT_REGULAR_NAME,
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#1E293B"),
                leftIndent=15,
                firstLineIndent=-10,
                spaceAfter=4,
            ),
            "CodeBlock": ParagraphStyle(
                "CodeBlock",
                fontName=FONT_REGULAR_NAME,
                fontSize=8.5,
                leading=12,
                textColor=colors.HexColor("#0F172A"),
                backColor=colors.HexColor("#F1F5F9"),
                borderColor=colors.HexColor("#CBD5E1"),
                borderWidth=0.5,
                borderPadding=6,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "Callout": ParagraphStyle(
                "Callout",
                fontName=FONT_REGULAR_NAME,
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#475569"),
                backColor=colors.HexColor("#F8FAFC"),
                borderColor=colors.HexColor("#3B82F6"),
                borderWidth=1,
                borderPadding=6,
                leftIndent=10,
                spaceBefore=6,
                spaceAfter=6,
            ),
        }

    def _format_inline_markdown(self, text: str) -> str:
        """Converts Markdown inline elements (*, **, `) into ReportLab XML."""
        escaped = html.escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"__(.+?)__", r"<b>\1</b>", escaped)
        escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)
        escaped = re.sub(r"`(.+?)`", f'<font face="{FONT_BOLD_NAME}" color="#0369A1">\\1</font>', escaped)
        return escaped

    def create_lecture_pdf(self, markdown_text: str, filename_prefix: str = "lecture") -> str:
        pdf_filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(settings.TEMP_DIR, pdf_filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        story = []
        lines = markdown_text.splitlines()

        in_code_block = False
        code_buffer = []

        # Add top banner
        banner_data = [
            [
                Paragraph("<b>ОЦИФРОВАННЫЙ КОНСПЕКТ</b>", ParagraphStyle(
                    "BannerTitle", fontName=FONT_BOLD_NAME, fontSize=13, leading=16, textColor=colors.HexColor("#1E3A8A")
                )),
                Paragraph(datetime.now().strftime("%d.%m.%Y"), ParagraphStyle(
                    "BannerDate", fontName=FONT_REGULAR_NAME, fontSize=9, leading=12, alignment=2, textColor=colors.HexColor("#64748B")
                ))
            ]
        ]
        t = Table(banner_data, colWidths=[380, 107])
        t.setStyle(TableStyle([
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor("#2563EB")),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

        for raw_line in lines:
            line = raw_line.rstrip()

            # Code blocks ```
            if line.strip().startswith("```"):
                if in_code_block:
                    block_content = html.escape("\n".join(code_buffer))
                    story.append(Paragraph(block_content.replace("\n", "<br/>"), self.styles["CodeBlock"]))
                    code_buffer = []
                    in_code_block = False
                else:
                    in_code_block = True
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # Empty lines
            if not line.strip():
                story.append(Spacer(1, 4))
                continue

            # Horizontal dividers
            if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", line.strip()):
                story.append(Spacer(1, 6))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=8, spaceBefore=4))
                continue

            # Headings
            if line.startswith("# "):
                title_text = self._format_inline_markdown(line[2:].strip())
                story.append(Paragraph(title_text, self.styles["Heading1"]))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#93C5FD"), spaceAfter=6, spaceBefore=2))
                continue
            elif line.startswith("## "):
                title_text = self._format_inline_markdown(line[3:].strip())
                story.append(Paragraph(title_text, self.styles["Heading2"]))
                continue
            elif line.startswith("### "):
                title_text = self._format_inline_markdown(line[4:].strip())
                story.append(Paragraph(title_text, self.styles["Heading3"]))
                continue

            # Blockquotes / Callouts
            if line.startswith("> "):
                callout_text = self._format_inline_markdown(line[2:].strip())
                story.append(Paragraph(callout_text, self.styles["Callout"]))
                continue

            # Bullet points
            bullet_match = re.match(r"^(\*|-|\+)\s+(.+)", line)
            if bullet_match:
                formatted_item = self._format_inline_markdown(bullet_match.group(2))
                story.append(Paragraph(f"• &nbsp; {formatted_item}", self.styles["Bullet"]))
                continue

            # Numbered lists
            num_match = re.match(r"^(\d+[\.\)])\s+(.+)", line)
            if num_match:
                num_prefix = num_match.group(1)
                formatted_item = self._format_inline_markdown(num_match.group(2))
                story.append(Paragraph(f"<b>{num_prefix}</b> &nbsp; {formatted_item}", self.styles["Bullet"]))
                continue

            # Regular paragraph
            body_text = self._format_inline_markdown(line)
            story.append(Paragraph(body_text, self.styles["Body"]))

        doc.build(story, canvasmaker=NumberedCanvas)
        return output_path

pdf_service = PDFService()
