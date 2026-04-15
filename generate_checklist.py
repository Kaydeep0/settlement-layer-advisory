#!/usr/bin/env python3
"""
Settlement Layer Advisory — Compliance Checklist PDF Generator
Platypus-based. Professional Helvetica body, drawn checkboxes,
full-page amber CTA on last page.
"""

import os
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, KeepTogether, Flowable, PageBreak
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── Colors ──────────────────────────────────────────────────────────────────────
BG      = HexColor('#0a0a0f')
TEXT    = HexColor('#e8e8e8')
ACCENT  = HexColor('#e8930a')
MUTED   = HexColor('#8a8aa0')
DARK    = HexColor('#0a0a0f')
BORDER2 = HexColor('#2a2a40')
WHITE   = HexColor('#ffffff')

# ── Page geometry ───────────────────────────────────────────────────────────────
W, H  = LETTER          # 612 × 792 pt
ML    = 60              # left margin
MR    = 60              # right margin
MT    = 72              # top margin
MB    = 72              # bottom margin
CW    = W - ML - MR    # 492 pt content width

FOOTER_Y      = 40
FOOTER_RULE_Y = 54

# Vertical space page-1 canvas header occupies (Spacer must match)
HEADER1_H = 145


# ── Helpers ─────────────────────────────────────────────────────────────────────
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


# ── Canvas layer: background / watermark / footer / headers ─────────────────────
def _bg(canvas):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.restoreState()


def _watermark(canvas):
    canvas.saveState()
    canvas.setFillColor(Color(0.6, 0.6, 0.6, alpha=0.035))
    canvas.setFont('Helvetica-Bold', 30)
    canvas.translate(306, 240)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, 'SETTLEMENT LAYER ADVISORY')
    canvas.restoreState()


def _footer(canvas, is_cta_page=False):
    if is_cta_page:
        return  # no footer on the amber CTA page
    canvas.setStrokeColor(BORDER2)
    canvas.setLineWidth(0.5)
    canvas.line(ML, FOOTER_RULE_Y, W - MR, FOOTER_RULE_Y)
    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawCentredString(
        W / 2, FOOTER_Y,
        ('Settlement Layer Advisory  |  Powered by Eigenstate Research  |  '
         'This checklist is for informational purposes only and does not '
         'constitute legal advice.')
    )


def _header_p1(canvas):
    """Full header drawn by canvas on page 1. Spacer in story reserves this space."""
    y = H - MT  # 720

    # Brand
    canvas.setFillColor(ACCENT)
    canvas.setFont('Helvetica-Bold', 13)
    canvas.drawString(ML, y, 'SETTLEMENT LAYER ADVISORY')
    y -= 18

    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 8.5)
    canvas.drawString(ML, y, 'Powered by Eigenstate Research')
    y -= 13

    # Rule
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.75)
    canvas.line(ML, y, W - MR, y)
    y -= 24

    # Title
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold', 22)
    canvas.drawString(ML, y, 'The RWA Protocol Compliance Checklist')
    y -= 28

    # Subtitle
    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica', 11)
    canvas.drawString(ML, y, 'What your tokenized offering needs before it touches a US investor')
    y -= 15

    # Source note
    canvas.setFont('Helvetica-Oblique', 8)
    for ln in _wrap(
        'Based on SEC January 28 2026 joint statement on tokenized securities, '
        'Securities Act of 1933, and current FINRA requirements',
        'Helvetica-Oblique', 8, CW
    ):
        canvas.drawString(ML, y, ln)
        y -= 11


def _header_p2plus(canvas):
    """Minimal running header for pages 2+, drawn in the top margin."""
    y = H - 44
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.4)
    canvas.line(ML, y, W - MR, y)
    canvas.setFillColor(ACCENT)
    canvas.setFont('Helvetica', 8.5)
    canvas.drawRightString(W - MR, y - 13, 'Settlement Layer Advisory')


def add_page_elements(canvas, doc):
    _bg(canvas)
    _watermark(canvas)
    is_cta = getattr(doc, '_cta_page', None) == doc.page
    _footer(canvas, is_cta_page=is_cta)
    if doc.page == 1:
        _header_p1(canvas)
    else:
        _header_p2plus(canvas)


# ── Flowable: SectionHeader ──────────────────────────────────────────────────────
class SectionHeader(Flowable):
    """Amber badge + title + amber rule + optional italic note line."""
    PAD_TOP  = 20
    BADGE_H  = 15
    RULE_GAP = 9
    NOTE_H   = 14
    PAD_BOT  = 8

    def __init__(self, num: str, title: str, note: str = None):
        super().__init__()
        self.num   = num
        self.title = title
        self.note  = note
        self.width = CW
        h = self.PAD_TOP + self.BADGE_H + self.RULE_GAP + self.PAD_BOT
        if note:
            h += self.NOTE_H + 4
        self.height = h

    def wrap(self, availW, availH):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # In local coords: (0,0) = bottom-left, y increases up.
        badge_bottom = self.height - self.PAD_TOP - self.BADGE_H

        # Badge
        badge_w = stringWidth(self.num, 'Helvetica-Bold', 8.5) + 14
        c.setFillColor(ACCENT)
        c.roundRect(0, badge_bottom, badge_w, self.BADGE_H, 2, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(7, badge_bottom + 3.5, self.num)

        # Title
        c.setFillColor(TEXT)
        c.setFont('Helvetica-Bold', 13)
        c.drawString(badge_w + 10, badge_bottom + 2, self.title)

        # Amber rule
        rule_y = badge_bottom - self.RULE_GAP
        c.setStrokeColor(ACCENT)
        c.setLineWidth(0.5)
        c.line(0, rule_y, self.width, rule_y)

        # Optional note
        if self.note:
            note_y = rule_y - self.NOTE_H
            c.setFillColor(MUTED)
            c.setFont('Helvetica-Oblique', 8)
            c.drawString(0, note_y, self.note)


# ── Flowable: CheckItem ──────────────────────────────────────────────────────────
class CheckItem(Flowable):
    """
    Professional checklist item: drawn amber-outlined checkbox square + Helvetica text.
    Text wraps cleanly within available width.
    """
    FONT      = 'Helvetica'
    FONT_SIZE = 10
    LEADING   = 15
    BOX       = 8.5    # checkbox square side length
    TEXT_X    = 20     # text indent

    def __init__(self, text: str):
        super().__init__()
        self._text  = text
        self.width  = CW
        self._lines = _wrap(text, self.FONT, self.FONT_SIZE, CW - self.TEXT_X)
        self.height = len(self._lines) * self.LEADING
        self.spaceAfter = 12

    def wrap(self, availW, availH):
        return self.width, self.height

    def draw(self):
        c = self.canv
        n = len(self._lines)

        # In local coords, line baselines (bottom to top):
        # last line at y=0, first line at y=(n-1)*LEADING
        y_first = (n - 1) * self.LEADING

        # Checkbox: bottom edge slightly below text baseline, top at cap height
        box_y = y_first - 1.0         # 1pt below baseline
        c.setStrokeColor(ACCENT)
        c.setFillColor(BG)
        c.setLineWidth(0.8)
        c.rect(0, box_y, self.BOX, self.BOX, fill=1, stroke=1)

        # Item text
        c.setFillColor(TEXT)
        c.setFont(self.FONT, self.FONT_SIZE)
        y = y_first
        for ln in self._lines:
            c.drawString(self.TEXT_X, y, ln)
            y -= self.LEADING


# ── Flowable: ClosingBox (full-page amber CTA) ───────────────────────────────────
class ClosingBox(Flowable):
    """
    Fills the available page height with an amber background.
    Content (heading, body, URL strip) is vertically centered.
    """
    PAD = 28

    def __init__(self, heading: str, paragraphs: list, url: str):
        super().__init__()
        self.heading    = heading
        self.paragraphs = paragraphs
        self.url        = url
        self.width      = CW
        self.height     = 648   # will be overridden by wrap()

    def _content_h(self, w: float) -> float:
        p     = self.PAD
        max_w = w - p * 2
        h     = 22 + 18  # heading + gap
        for para in self.paragraphs:
            h += len(_wrap(para, 'Helvetica', 10.5, max_w)) * 16 + 10
        url_lines = _wrap(self.url, 'Helvetica-Bold', 10.5, max_w - 16)
        h += len(url_lines) * 16 + 20   # url inset strip
        return h

    def wrap(self, availW, availH):
        self.width  = min(availW, CW)
        # Fill the full available page height so this becomes a CTA page
        self.height = max(availH, self._content_h(self.width))
        return self.width, self.height

    def draw(self):
        c     = self.canv
        p     = self.PAD
        max_w = self.width - p * 2

        # Full amber background
        c.setFillColor(ACCENT)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # Vertically center content
        content_h = self._content_h(self.width)
        # y_top: top of content block in local coords (y up from bottom)
        y_top = (self.height + content_h) / 2

        y = y_top

        # Heading
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(p, y - 16, self.heading)
        y -= 40

        # Body paragraphs
        c.setFont('Helvetica', 10.5)
        for para in self.paragraphs:
            for ln in _wrap(para, 'Helvetica', 10.5, max_w):
                c.drawString(p, y - 13, ln)
                y -= 16
            y -= 10

        # URL strip (dark inset)
        url_lines = _wrap(self.url, 'Helvetica-Bold', 10.5, max_w - 16)
        strip_h   = len(url_lines) * 16 + 16
        strip_y   = y - strip_h - 2
        c.setFillColor(DARK)
        c.roundRect(p - 6, strip_y, self.width - (p - 6) * 2, strip_h, 4, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.setFont('Helvetica-Bold', 10.5)
        ty = y - 13
        for ln in url_lines:
            c.drawString(p, ty, ln)
            ty -= 16


# ── Content ─────────────────────────────────────────────────────────────────────
SECTION_1 = [
    ('Confirmed whether your token is issuer-sponsored or third-party tokenized '
     'security under the SEC January 28 2026 joint statement.'),
    ('Determined whether your structure is custodial or synthetic. Synthetic '
     'structures may qualify as security-based swaps requiring additional registration.'),
    ('Offering registered under Securities Act of 1933 or valid exemption confirmed. '
     'Reg D Rule 506(b) or 506(c), or Reg S for offshore.'),
    'Form D filed with SEC EDGAR within 15 days of first sale if using Reg D.',
    ('General solicitation rules confirmed. Rule 506(b) prohibits general '
     'solicitation. Rule 506(c) permits it only if all purchasers are verified '
     'accredited investors.'),
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


# ── Story builder ────────────────────────────────────────────────────────────────
def _section(num: str, title: str, items: list, note: str = None) -> list:
    """Returns flowables for one section: header kept with first item."""
    header = SectionHeader(num, title, note=note)
    first  = CheckItem(items[0])
    block  = [KeepTogether([header, first])]
    for text in items[1:]:
        block.append(CheckItem(text))
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

    # Page 1: reserve space for canvas-drawn header
    story.append(Spacer(1, HEADER1_H))

    # Sections 1–4
    story.extend(_section('SECTION 1', 'OFFERING STRUCTURE', SECTION_1))
    story.extend(_section('SECTION 2', 'INVESTOR ONBOARDING', SECTION_2,
                          note='Requires licensed professional'))
    story.extend(_section('SECTION 3', 'SMART CONTRACT AND SETTLEMENT COMPLIANCE', SECTION_3))
    story.extend(_section('SECTION 4', 'ONGOING COMPLIANCE', SECTION_4))

    # Force the CTA onto its own clean page
    story.append(PageBreak())
    story.append(ClosingBox(
        heading='HOW MANY OF THESE ARE UNCHECKED?',
        paragraphs=CLOSING_PARAS,
        url=CLOSING_URL,
    ))

    # Tag the last page number so the callback can skip the footer there
    # (We don't know it ahead of time, so ClosingBox handles the amber bg itself
    #  and the canvas footer simply renders below it in the page margin — fine.)

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
