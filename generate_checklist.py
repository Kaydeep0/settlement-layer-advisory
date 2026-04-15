#!/usr/bin/env python3
"""
Settlement Layer Advisory — Compliance Checklist PDF Generator
Rewritten using ReportLab Platypus for reliable multi-page layout.
"""

import os
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle,
    KeepTogether, Flowable, Paragraph
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── Colors ─────────────────────────────────────────────────────────────────────
BG      = HexColor('#0a0a0f')
TEXT    = HexColor('#e8e8e8')
ACCENT  = HexColor('#e8930a')
MUTED   = HexColor('#8a8aa0')
DARK    = HexColor('#0a0a0f')
BORDER2 = HexColor('#2a2a40')

# ── Page geometry ───────────────────────────────────────────────────────────────
W, H   = LETTER          # 612 x 792 pt
ML     = 60              # left margin
MR     = 60              # right margin
MT     = 72              # top margin
MB     = 72              # bottom margin
CW     = W - ML - MR    # content width: 492 pt

FOOTER_Y      = 42
FOOTER_RULE_Y = 55

# Height the canvas header occupies on page 1 (Spacer must match this).
# Calculated from top of content area (y=720) to end of source text + 24pt gap.
HEADER1_H = 158


# ── Text-wrap helper ────────────────────────────────────────────────────────────
def _wrap(text: str, font: str, size: float, max_w: float) -> list:
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if stringWidth(test, font, size) <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [w]
    if cur:
        lines.append(' '.join(cur))
    return lines or ['']


# ── Canvas callbacks ────────────────────────────────────────────────────────────
def _draw_bg_watermark_footer(canvas, doc):
    """Dark background, diagonal watermark, footer rule and text."""
    # Background
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.restoreState()

    # Watermark
    canvas.saveState()
    canvas.setFillColor(Color(0.9, 0.9, 0.9, alpha=0.03))
    canvas.setFont('Helvetica-Bold', 42)
    canvas.translate(306, 396)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, 'SETTLEMENT LAYER ADVISORY')
    canvas.restoreState()

    # Footer rule
    canvas.setStrokeColor(BORDER2)
    canvas.setLineWidth(0.5)
    canvas.line(ML, FOOTER_RULE_Y, W - MR, FOOTER_RULE_Y)

    # Footer text
    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(
        W / 2, FOOTER_Y,
        ('Settlement Layer Advisory  |  Powered by Eigenstate Research  |  '
         'This checklist is for informational purposes only and does not '
         'constitute legal advice.')
    )


def _draw_header_p1(canvas, doc):
    """Full header block on page 1, drawn from top of content area downward."""
    y = H - MT  # 720

    canvas.setFillColor(ACCENT)
    canvas.setFont('Helvetica-Bold', 14)
    canvas.drawString(ML, y, 'SETTLEMENT LAYER ADVISORY')
    y -= 20

    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 9)
    canvas.drawString(ML, y, 'Powered by Eigenstate Research')
    y -= 14

    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.0)
    canvas.line(ML, y, W - MR, y)
    y -= 6

    y -= 20  # space below rule

    canvas.setFillColor(TEXT)
    canvas.setFont('Helvetica-Bold', 24)
    canvas.drawString(ML, y, 'The RWA Protocol Compliance Checklist')
    y -= 32

    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 12)
    canvas.drawString(ML, y, 'What your tokenized offering needs before it touches a US investor')
    y -= 18

    canvas.setFont('Helvetica-Oblique', 8)
    source = ('Based on SEC January 28 2026 joint statement on tokenized securities, '
              'Securities Act of 1933, and current FINRA requirements')
    for ln in _wrap(source, 'Helvetica-Oblique', 8, CW):
        canvas.drawString(ML, y, ln)
        y -= 11


def _draw_header_p2plus(canvas, doc):
    """Minimal header for pages 2+, drawn within the top margin."""
    y = H - 46  # within the 72pt top margin

    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.5)
    canvas.line(ML, y, W - MR, y)

    canvas.setFillColor(ACCENT)
    canvas.setFont('Helvetica', 9)
    canvas.drawRightString(W - MR, y - 14, 'Settlement Layer Advisory')


def add_page_elements(canvas, doc):
    _draw_bg_watermark_footer(canvas, doc)
    if doc.page == 1:
        _draw_header_p1(canvas, doc)
    else:
        _draw_header_p2plus(canvas, doc)


# ── Custom flowables ────────────────────────────────────────────────────────────

class SectionHeader(Flowable):
    """
    Amber badge + section title + amber rule + optional italic note.
    Layout (bottom to top in PDF local coords):
        PAD_BOT | [note+gap] | rule | gap | [badge/title row] | PAD_TOP
    """
    PAD_TOP  = 10
    BADGE_H  = 16
    RULE_GAP = 8
    NOTE_H   = 14   # note line height including gap below
    PAD_BOT  = 12

    def __init__(self, num: str, title: str, note: str = None):
        super().__init__()
        self.num   = num
        self.title = title
        self.note  = note
        self.width = CW
        self.height = (self.PAD_TOP + self.BADGE_H + self.RULE_GAP
                       + (self.NOTE_H if note else 0) + self.PAD_BOT)

    def wrap(self, availW, availH):
        return self.width, self.height

    def draw(self):
        c = self.canv
        h = self.height

        # Badge + title row sits at top of flowable
        badge_y = h - self.PAD_TOP - self.BADGE_H

        badge_w = stringWidth(self.num, 'Helvetica-Bold', 9) + 16
        c.setFillColor(ACCENT)
        c.roundRect(0, badge_y, badge_w, self.BADGE_H, 2, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(8, badge_y + 4, self.num)

        c.setFillColor(TEXT)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(badge_w + 10, badge_y + 3, self.title)

        # Amber rule
        rule_y = badge_y - self.RULE_GAP
        c.setStrokeColor(ACCENT)
        c.setLineWidth(0.5)
        c.line(0, rule_y, self.width, rule_y)

        # Optional note
        if self.note:
            note_y = rule_y - self.NOTE_H + 2
            c.setFillColor(MUTED)
            c.setFont('Helvetica-Oblique', 8)
            c.drawString(0, note_y, self.note)


class ClosingBox(Flowable):
    """Amber-background CTA box with dark text and dark inset URL strip."""

    PAD = 20

    def __init__(self, heading: str, paragraphs: list, url: str):
        super().__init__()
        self.heading    = heading
        self.paragraphs = paragraphs
        self.url        = url
        self.width      = CW
        self.height     = self._calc_height(CW)

    def _calc_height(self, w: float) -> float:
        p     = self.PAD
        max_w = w - p * 2
        h     = p + 18 + 10   # top pad + heading + gap
        for para in self.paragraphs:
            h += len(_wrap(para, 'Helvetica', 10, max_w)) * 14 + 8
        url_lines = _wrap(self.url, 'Helvetica-Bold', 10, max_w - 8)
        h += len(url_lines) * 14 + 16   # inset box
        h += p                           # bottom pad
        return h

    def wrap(self, availW, availH):
        self.width  = min(availW, CW)
        self.height = self._calc_height(self.width)
        return self.width, self.height

    def draw(self):
        c     = self.canv
        p     = self.PAD
        max_w = self.width - p * 2

        # Amber background
        c.setFillColor(ACCENT)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)

        # Draw from top downward; y is baseline cursor
        y = self.height - p

        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 12)
        c.drawString(p, y - 14, self.heading)
        y -= 28   # heading height + gap

        c.setFont('Helvetica', 10)
        for para in self.paragraphs:
            for ln in _wrap(para, 'Helvetica', 10, max_w):
                c.drawString(p, y - 12, ln)
                y -= 14
            y -= 8

        # Dark inset URL strip
        url_lines = _wrap(self.url, 'Helvetica-Bold', 10, max_w - 8)
        inset_h   = len(url_lines) * 14 + 12
        inset_y   = y - inset_h
        c.setFillColor(DARK)
        c.roundRect(p - 4, inset_y, self.width - p * 2 + 8, inset_h, 3, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.setFont('Helvetica-Bold', 10)
        ty = y - 12
        for ln in url_lines:
            c.drawString(p, ty, ln)
            ty -= 14


# ── Styles ──────────────────────────────────────────────────────────────────────
_CHECKBOX_STYLE = ParagraphStyle(
    'Checkbox',
    fontName='Courier-Bold',
    fontSize=10,
    textColor=ACCENT,
    leading=14,
    spaceBefore=0,
    spaceAfter=0,
)

_ITEM_STYLE = ParagraphStyle(
    'ItemText',
    fontName='Courier',
    fontSize=10,
    textColor=TEXT,
    leading=14,
    spaceBefore=0,
    spaceAfter=0,
)


# ── Checklist item factory ──────────────────────────────────────────────────────
def _item(text: str) -> Table:
    """Two-column table: amber [ ] | item text, with 8pt space after."""
    tbl = Table(
        [[Paragraph('[ ]', _CHECKBOX_STYLE), Paragraph(text, _ITEM_STYLE)]],
        colWidths=[22, CW - 22],
    )
    tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    tbl.spaceAfter = 8
    return tbl


# ── Content ─────────────────────────────────────────────────────────────────────
SECTION_1 = [
    ('Confirmed whether your token is issuer-sponsored or third-party tokenized '
     'security under the SEC January 28 2026 joint statement.'),
    ('Determined whether your structure is custodial or synthetic. Synthetic '
     'structures may qualify as security-based swaps requiring additional registration.'),
    ('Offering registered under Securities Act of 1933 or valid exemption confirmed. '
     'Reg D Rule 506(b) or 506(c), or Reg S for offshore.'),
    'Form D filed with SEC EDGAR within 15 days of first sale if using Reg D.',
    ('General solicitation rules confirmed. Rule 506(b) prohibits general solicitation. '
     'Rule 506(c) permits it only if all purchasers are verified accredited investors.'),
    ('Master securityholder file structure documented. Onchain records legally '
     'tied to offchain ownership registry.'),
    ('Token rights mapped against underlying security rights. Material differences '
     'may create a separate class of security requiring independent registration.'),
]

SECTION_2 = [
    ('Accredited investor status verified for every US purchaser. Income above '
     '$200K individual / $300K joint, or net worth above $1M excluding primary '
     'residence, or Series 7 / 65 / 82 license holder.'),
    ('Verification performed by a licensed securities professional (Series 7 or '
     'Series 66). Self-certification alone does not satisfy Rule 506(c) '
     'reasonable steps requirement.'),
    ('KYC completed per FinCEN requirements. Government-issued ID, proof of '
     'address, beneficial ownership documentation.'),
    'AML screening completed against OFAC SDN list and relevant sanctions programs.',
    ('Suitability assessment documented. Investment objectives, risk tolerance, '
     'financial situation on file.'),
    'Investor representations and warranties executed and countersigned.',
    'State Blue Sky law requirements confirmed for each investor state of residence.',
]

SECTION_3 = [
    ('Transfer restrictions encoded in smart contract match offering document '
     'restrictions exactly.'),
    ('Resale restrictions enforced onchain. Rule 506 securities are restricted '
     'and cannot be freely resold without registration or exemption.'),
    ('Investor eligibility checks automated at point of secondary transfer. '
     'Permissioned transfer mechanism in place.'),
    ('FINRA and SEC jurisdictional overlap reviewed for custody structure. '
     'Identify the registered broker-dealer or transfer agent.'),
    'On-chain settlement finality documented against applicable clearing rules.',
    ('Wallet address to investor identity mapping maintained and reconciled '
     'against offchain records.'),
]

SECTION_4 = [
    ('Antifraud provisions confirmed. All investor communications free from '
     'false or misleading statements per Securities Act Section 17(a).'),
    'Reporting obligations confirmed under Exchange Act if applicable.',
    ('Investment Company Act of 1940 applicability assessed if structure '
     'resembles a pooled fund.'),
    ('Regulatory monitoring in place. SEC, CFTC, FINRA, and OCC positions '
     'tracked as guidance evolves.'),
    ('State securities regulator notifications filed where required '
     'for Reg D Rule 504 offerings.'),
]

CLOSING_PARAS = [
    'Most protocols we review have gaps in Section 2 and Section 3.',
    ('Section 2 requires a licensed securities professional. Your engineers '
     'cannot satisfy the Rule 506(c) verification requirement regardless of '
     'what your legal counsel advises.'),
    ('Settlement Layer Advisory closes these gaps. Licensed Series 7 and Series 66 '
     'professionals handle investor verification. Compliance auditors review your '
     'offering structure against current SEC guidance. Eigenstate Research monitors '
     'the regulatory field so you know where pressure is building before it '
     'reaches your protocol.'),
]

CLOSING_URL = 'kaydeep0.github.io/settlement-layer-advisory'


# ── Build ────────────────────────────────────────────────────────────────────────
def _section(num, title, items, note=None):
    """Returns a list of flowables for one section."""
    header = SectionHeader(num, title, note=note)
    # Keep header + first item together to prevent orphan headers
    block = [KeepTogether([header, _item(items[0])])]
    for text in items[1:]:
        block.append(_item(text))
    return block


def build(out_path: str):
    doc = SimpleDocTemplate(
        out_path,
        pagesize=LETTER,
        leftMargin=ML,
        rightMargin=MR,
        topMargin=MT,
        bottomMargin=MB,
        title='The RWA Protocol Compliance Checklist',
        author='Settlement Layer Advisory',
        subject='Powered by Eigenstate Research',
    )

    story = []

    # Reserve space on page 1 for the canvas-drawn header
    story.append(Spacer(1, HEADER1_H))

    # Sections
    story.extend(_section('SECTION 1', 'OFFERING STRUCTURE', SECTION_1))
    story.extend(_section('SECTION 2', 'INVESTOR ONBOARDING', SECTION_2,
                          note='Requires licensed professional'))
    story.extend(_section('SECTION 3', 'SMART CONTRACT AND SETTLEMENT COMPLIANCE', SECTION_3))
    story.extend(_section('SECTION 4', 'ONGOING COMPLIANCE', SECTION_4))

    # Closing box
    story.append(Spacer(1, 16))
    story.append(ClosingBox(
        heading='HOW MANY OF THESE ARE UNCHECKED?',
        paragraphs=CLOSING_PARAS,
        url=CLOSING_URL,
    ))

    doc.build(
        story,
        onFirstPage=add_page_elements,
        onLaterPages=add_page_elements,
    )

    size = os.path.getsize(out_path)
    print(f'PDF written: {out_path}  ({size:,} bytes)')


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'checklist.pdf')
    build(out)
