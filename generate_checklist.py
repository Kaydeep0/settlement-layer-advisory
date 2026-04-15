#!/usr/bin/env python3
"""
Settlement Layer Advisory — Compliance Checklist PDF Generator
Produces checklist.pdf using reportlab canvas for full layout control.
"""

import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── Colors ────────────────────────────────────────────────────────────────────
BG      = HexColor('#0a0a0f')
CARD    = HexColor('#111120')
TEXT    = HexColor('#e8e8e8')
ACCENT  = HexColor('#e8930a')
MUTED   = HexColor('#8a8aa0')
BORDER  = HexColor('#1e1e30')
WHITE   = HexColor('#ffffff')
GRAY    = HexColor('#888888')
DARK    = HexColor('#0a0a0f')

# ── Page geometry ─────────────────────────────────────────────────────────────
W, H        = LETTER          # 612 x 792 pts
ML          = 60              # margin left
MR          = W - 60          # margin right
CW          = MR - ML         # content width = 492
FOOTER_Y    = 28
FOOTER_LINE = FOOTER_Y + 14
TOP_START   = H - 58          # first y position after top margin


# ── Text wrapping ─────────────────────────────────────────────────────────────
def wrap(text: str, font: str, size: float, max_width: float) -> list:
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if stringWidth(test, font, size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [w]
    if cur:
        lines.append(' '.join(cur))
    return lines or ['']


# ── PDF builder ───────────────────────────────────────────────────────────────
class ChecklistPDF:
    def __init__(self, path: str):
        self.c = canvas.Canvas(path, pagesize=LETTER)
        self.c.setTitle('The RWA Protocol Compliance Checklist')
        self.c.setAuthor('Settlement Layer Advisory')
        self.c.setSubject('Powered by Eigenstate Research')
        self.y   = TOP_START
        self.pg  = 0

    # ── Page control ──────────────────────────────────────────────────────────
    def _bg(self):
        self.c.setFillColor(BG)
        self.c.rect(0, 0, W, H, fill=1, stroke=0)

    def _footer(self):
        self.c.setStrokeColor(ACCENT)
        self.c.setLineWidth(0.4)
        self.c.line(ML, FOOTER_LINE, MR, FOOTER_LINE)
        self.c.setFillColor(MUTED)
        self.c.setFont('Helvetica', 6.5)
        txt = ('Settlement Layer Advisory  |  Powered by Eigenstate Research  |  '
               'This checklist is for informational purposes only and does not '
               'constitute legal advice.')
        self.c.drawCentredString(W / 2, FOOTER_Y, txt)

    def _watermark(self):
        self.c.saveState()
        self.c.setFillColor(GRAY)
        self.c.setFillAlpha(0.03)
        self.c.setFont('Helvetica-Bold', 36)
        self.c.translate(W / 2, 200)
        self.c.rotate(45)
        self.c.drawCentredString(0, 0, 'SETTLEMENT LAYER ADVISORY')
        self.c.restoreState()

    def new_page(self):
        if self.pg > 0:
            self._footer()
            self.c.showPage()
        self.pg += 1
        self._bg()
        self._watermark()
        self.y = TOP_START

    def need_page(self, pts: float) -> bool:
        return self.y - pts < FOOTER_LINE + 30

    def gap(self, pts: float):
        self.y -= pts

    # ── Drawing primitives ────────────────────────────────────────────────────
    def line_text(self, text: str, font: str, size: float, color: HexColor,
                  x: float = None, leading: float = None) -> float:
        """Draw one wrapped block, return height used."""
        if x is None:
            x = ML
        max_w = MR - x
        lines = wrap(text, font, size, max_w)
        lh = leading or size * 1.55
        for ln in lines:
            self.c.setFillColor(color)
            self.c.setFont(font, size)
            self.c.drawString(x, self.y, ln)
            self.y -= lh
        return len(lines) * lh

    def draw_rule(self, color: HexColor = None, lw: float = 0.75):
        self.c.setStrokeColor(color or ACCENT)
        self.c.setLineWidth(lw)
        self.c.line(ML, self.y, MR, self.y)
        self.y -= 6

    def draw_rect_bg(self, x, y, w, h, fill: HexColor):
        self.c.setFillColor(fill)
        self.c.rect(x, y, w, h, fill=1, stroke=0)

    # ── Composed elements ─────────────────────────────────────────────────────
    def header(self):
        """First page header block."""
        # Brand name
        self.c.setFillColor(WHITE)
        self.c.setFont('Helvetica-Bold', 15)
        self.c.drawString(ML, self.y, 'SETTLEMENT LAYER ADVISORY')
        self.y -= 20

        self.c.setFillColor(MUTED)
        self.c.setFont('Helvetica', 8)
        self.c.drawString(ML, self.y, 'Powered by Eigenstate Research')
        self.y -= 18

        self.draw_rule(ACCENT, 1.0)
        self.y -= 10

    def title_block(self):
        self.c.setFillColor(WHITE)
        self.c.setFont('Helvetica-Bold', 22)
        self.c.drawString(ML, self.y, 'The RWA Protocol Compliance Checklist')
        self.y -= 26

        self.c.setFillColor(TEXT)
        self.c.setFont('Helvetica', 11)
        self.c.drawString(ML, self.y, 'What your tokenized offering needs before it touches a US investor')
        self.y -= 20

        self.c.setFillColor(MUTED)
        self.c.setFont('Helvetica-Oblique', 7.5)
        source = ('Based on SEC January 28 2026 joint statement on tokenized securities, '
                  'Securities Act of 1933, and current FINRA requirements')
        lines = wrap(source, 'Helvetica-Oblique', 7.5, CW)
        for ln in lines:
            self.c.drawString(ML, self.y, ln)
            self.y -= 11
        self.y -= 10

    def section_header(self, num: str, title: str):
        needed = 36
        if self.need_page(needed):
            self.new_page()
        self.y -= 20
        # Number badge
        badge_w = stringWidth(num, 'Helvetica-Bold', 8) + 14
        self.c.setFillColor(ACCENT)
        self.c.roundRect(ML, self.y - 2, badge_w, 14, 2, fill=1, stroke=0)
        self.c.setFillColor(DARK)
        self.c.setFont('Helvetica-Bold', 8)
        self.c.drawString(ML + 7, self.y + 3, num)
        # Title
        self.c.setFillColor(ACCENT)
        self.c.setFont('Helvetica-Bold', 11)
        self.c.drawString(ML + badge_w + 8, self.y + 3, title)
        self.y -= 20

        # Thin amber underline
        self.c.setStrokeColor(ACCENT)
        self.c.setLineWidth(0.4)
        self.c.line(ML, self.y, MR, self.y)
        self.y -= 10

    def section_note(self, note: str):
        self.c.setFillColor(MUTED)
        self.c.setFont('Helvetica-Oblique', 8)
        self.c.drawString(ML, self.y, note)
        self.y -= 22  # 12pt text descent + 10pt gap before first item

    def checkbox_item(self, text: str):
        """Draw a checkbox row with [ ] in amber and wrapped text in Courier."""
        font       = 'Courier'
        font_size  = 10
        leading    = 18
        box_str    = '[ ]'
        box_w      = stringWidth(box_str, 'Courier-Bold', font_size) + 6
        text_x     = ML + box_w
        max_text_w = MR - text_x

        lines = wrap(text, font, font_size, max_text_w)
        total_h = len(lines) * leading + 8  # 8pt padding below item

        if self.need_page(total_h):
            self.new_page()

        # Checkbox
        self.c.setFillColor(ACCENT)
        self.c.setFont('Courier-Bold', font_size)
        self.c.drawString(ML, self.y, box_str)

        # Text lines
        self.c.setFillColor(TEXT)
        self.c.setFont(font, font_size)
        for i, ln in enumerate(lines):
            self.c.drawString(text_x, self.y, ln)
            self.y -= leading

        self.y -= 10  # inter-item spacing

    def closing_box(self, heading: str, paragraphs: list, final_line: str):
        """Amber-background box for the closing call to action."""
        font_h   = 'Helvetica-Bold'
        font_b   = 'Helvetica'
        size_h   = 12
        size_b   = 8.5
        leading  = 13
        pad      = 20

        # Pre-calculate height
        heading_h = 20
        total_h   = heading_h + pad
        all_lines = []
        for para in paragraphs:
            ls = wrap(para, font_b, size_b, CW - pad * 2)
            all_lines.append(ls)
            total_h += len(ls) * leading + 10
        # final line
        fl_lines = wrap(final_line, 'Courier-Bold', size_b, CW - pad * 2)
        total_h += len(fl_lines) * leading + pad

        if self.need_page(total_h + 20):
            self.new_page()

        self.y -= 12
        box_y = self.y - total_h
        box_h = total_h

        # Draw amber background
        self.c.setFillColor(ACCENT)
        self.c.roundRect(ML, box_y, CW, box_h, 4, fill=1, stroke=0)

        # Draw content
        ty = self.y - pad

        self.c.setFillColor(DARK)
        self.c.setFont(font_h, size_h)
        self.c.drawString(ML + pad, ty, heading)
        ty -= heading_h

        for ln_group in all_lines:
            for ln in ln_group:
                self.c.setFillColor(DARK)
                self.c.setFont(font_b, size_b)
                self.c.drawString(ML + pad, ty, ln)
                ty -= leading
            ty -= 8

        # Final amber-on-dark inset line
        inset_x = ML + pad
        inset_w = CW - pad * 2
        inset_h = len(fl_lines) * leading + 10
        self.c.setFillColor(DARK)
        self.c.roundRect(inset_x - 4, ty - inset_h + leading, inset_w + 8, inset_h, 3, fill=1, stroke=0)
        self.c.setFillColor(ACCENT)
        self.c.setFont('Courier-Bold', size_b)
        for ln in fl_lines:
            self.c.drawString(inset_x, ty, ln)
            ty -= leading

        self.y = box_y - 10

    def save(self):
        self._footer()
        self.c.save()


# ── Content ───────────────────────────────────────────────────────────────────
SECTION_1 = [
    ('Confirmed whether your token is issuer-sponsored or third-party tokenized '
     'security under the SEC January 28 2026 joint statement.'),
    ('Determined whether your structure is custodial or synthetic. Synthetic '
     'structures may qualify as security-based swaps requiring additional registration.'),
    ('Offering registered under Securities Act of 1933 or valid exemption confirmed. '
     'Reg D Rule 506(b) or 506(c), or Reg S for offshore.'),
    ('Form D filed with SEC EDGAR within 15 days of first sale if using Reg D.'),
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
    ('AML screening completed against OFAC SDN list and relevant sanctions programs.'),
    ('Suitability assessment documented. Investment objectives, risk tolerance, '
     'financial situation on file.'),
    ('Investor representations and warranties executed and countersigned.'),
    ('State Blue Sky law requirements confirmed for each investor state of residence.'),
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
    ('On-chain settlement finality documented against applicable clearing rules.'),
    ('Wallet address to investor identity mapping maintained and reconciled '
     'against offchain records.'),
]

SECTION_4 = [
    ('Antifraud provisions confirmed. All investor communications free from '
     'false or misleading statements per Securities Act Section 17(a).'),
    ('Reporting obligations confirmed under Exchange Act if applicable.'),
    ('Investment Company Act of 1940 applicability assessed if structure '
     'resembles a pooled fund.'),
    ('Regulatory monitoring in place. SEC, CFTC, FINRA, and OCC positions '
     'tracked as guidance evolves.'),
    ('State securities regulator notifications filed where required '
     'for Reg D Rule 504 offerings.'),
]

CLOSING_PARAS = [
    ('Most protocols we review have gaps in Section 2 and Section 3.'),
    ('Section 2 requires a licensed securities professional. Your engineers '
     'cannot satisfy the Rule 506(c) verification requirement regardless of '
     'what your legal counsel advises.'),
    ('Settlement Layer Advisory closes these gaps. Licensed Series 7 and Series 66 '
     'professionals handle investor verification. Compliance auditors review your '
     'offering structure against current SEC guidance. Eigenstate Research monitors '
     'the regulatory field so you know where pressure is building before it '
     'reaches your protocol.'),
]

CLOSING_FINAL = 'Request a briefing:  kaydeep0.github.io/settlement-layer-advisory'


# ── Build ─────────────────────────────────────────────────────────────────────
def build(out_path: str):
    pdf = ChecklistPDF(out_path)

    pdf.new_page()
    pdf.header()
    pdf.title_block()

    pdf.section_header('SECTION 1', 'OFFERING STRUCTURE')
    for item in SECTION_1:
        pdf.checkbox_item(item)

    pdf.section_header('SECTION 2', 'INVESTOR ONBOARDING')
    pdf.section_note('Requires licensed professional')
    for item in SECTION_2:
        pdf.checkbox_item(item)

    pdf.section_header('SECTION 3', 'SMART CONTRACT AND SETTLEMENT COMPLIANCE')
    for item in SECTION_3:
        pdf.checkbox_item(item)

    pdf.section_header('SECTION 4', 'ONGOING COMPLIANCE')
    for item in SECTION_4:
        pdf.checkbox_item(item)

    pdf.closing_box(
        heading='HOW MANY OF THESE ARE UNCHECKED?',
        paragraphs=CLOSING_PARAS,
        final_line=CLOSING_FINAL,
    )

    pdf.save()
    print(f'PDF written: {out_path}  ({os.path.getsize(out_path):,} bytes)')


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(__file__), 'checklist.pdf')
    build(out)
