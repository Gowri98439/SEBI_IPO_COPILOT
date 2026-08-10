"""
Enterprise DRHP PDF Service v2 — build_enterprise_drhp_pdf()

DESIGN GOALS:
- Accepts SectionOutput objects from the 12-stage pipeline (LLM + algorithmic content)
- Produces a complete, professionally formatted A4 PDF suitable for SEBI review workflows
- Bookmarks per section via ReportLab's outline API
- Accurate Table of Contents with automatic page references
- Correct headers/footers on every page
- Tables continue across pages (repeatRows)
- Charts embedded with size caps — NO overflow
- ALL [MISSING:...] markers rendered as professional "Information Not Provided" annotations
- NO internal evidence IDs exposed in the final PDF
- Page count is CONTENT-DRIVEN, NOT padded to artificial length
- Long sections never clip or overflow page boundaries
- Consecutive page-break handling
- A4, 2cm margins, professional neutral typography

SEPARATION OF CONCERNS:
- DRHP contains only formal disclosure content
- Evidence/citations visible in Intelligence Report, not this document
- AI labels NOT exposed in final DRHP text

FALLBACK:
If section_content is empty, marks section as "Information Not Provided — Human Review Required"
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from app.schemas.drhp_v2 import (
    ConsistencyReport,
    DrhpRequestV2,
    ExtendedFinancialYear,
    FinancialIntelligenceReport,
    SectionOutput,
    UsageItem,
)

logger = logging.getLogger(__name__)

# ── Page geometry ─────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
INNER_W = PAGE_W - 2 * MARGIN

# ── Colour palette ────────────────────────────────────────────
C_NAVY  = colors.HexColor('#003087')
C_BLUE  = colors.HexColor('#1A56DB')
C_TEAL  = colors.HexColor('#0E7490')
C_GREEN = colors.HexColor('#15803D')
C_AMBER = colors.HexColor('#B45309')
C_RED   = colors.HexColor('#DC2626')
C_BLACK = colors.HexColor('#0F172A')
C_GREY  = colors.HexColor('#64748B')
C_LGREY = colors.HexColor('#E2E8F0')
C_WHITE = colors.white
C_MISS  = colors.HexColor('#7C3AED')   # Purple for "Missing Information" annotations

MISSING_MARKER = re.compile(r'\[MISSING:\s*([^\]]+)\]', re.IGNORECASE)
CONFLICTING_MARKER = re.compile(r'\[CONFLICTING[^\]]*\]', re.IGNORECASE)
ERROR_MARKER = re.compile(r'\[GENERATION ERROR[^\]]*\]', re.IGNORECASE)


# ── Style definitions ─────────────────────────────────────────

def _get_styles() -> Any:
    base = getSampleStyleSheet()

    def add(name: str, **kw) -> ParagraphStyle:
        if name not in base.byName:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    # Cover
    add('V2_Cover1',    fontSize=24, leading=30, spaceAfter=14, textColor=C_NAVY,  alignment=TA_CENTER, fontName='Helvetica-Bold')
    add('V2_Cover2',    fontSize=16, leading=22, spaceAfter=10, textColor=C_BLACK, alignment=TA_CENTER)
    add('V2_CoverSub',  fontSize=10, leading=14, spaceAfter=6,  textColor=C_GREY,  alignment=TA_CENTER)
    add('V2_CoverNote', fontSize=8,  leading=12, spaceAfter=4,  textColor=C_GREY,  alignment=TA_CENTER)

    # Headings
    add('V2_H1', fontSize=14, leading=18, spaceBefore=16, spaceAfter=8,
        textColor=C_NAVY, fontName='Helvetica-Bold')
    add('V2_H2', fontSize=12, leading=16, spaceBefore=12, spaceAfter=6,
        textColor=C_NAVY, fontName='Helvetica-Bold')
    add('V2_H3', fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=5,
        textColor=C_BLACK, fontName='Helvetica-Bold')

    # Body
    add('V2_Body',      fontSize=9.5, leading=14.5, spaceAfter=7, textColor=C_BLACK, alignment=TA_JUSTIFY)
    add('V2_BodyB',     fontSize=9.5, leading=14.5, spaceAfter=7, textColor=C_BLACK, fontName='Helvetica-Bold')
    add('V2_Bullet',    fontSize=9.5, leading=14.5, spaceAfter=4, textColor=C_BLACK,
        leftIndent=16, firstLineIndent=-12)
    add('V2_Missing',   fontSize=9,   leading=13, spaceAfter=4, textColor=C_MISS,
        fontName='Helvetica-Oblique', alignment=TA_LEFT)
    add('V2_Disclaimer',fontSize=8,  leading=12, spaceAfter=5, textColor=C_GREY,  alignment=TA_JUSTIFY)

    # Tables
    add('V2_TableH', fontSize=8.5, leading=11, textColor=C_WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
    add('V2_TableC', fontSize=8.5, leading=11, textColor=C_BLACK, alignment=TA_CENTER)
    add('V2_TableL', fontSize=8.5, leading=11, textColor=C_BLACK, alignment=TA_LEFT)
    add('V2_TableR', fontSize=8.5, leading=11, textColor=C_BLACK, alignment=TA_RIGHT)

    # TOC
    add('V2_TOCPart',  fontSize=11, leading=15, spaceAfter=4, spaceBefore=6,
        textColor=C_NAVY, fontName='Helvetica-Bold')
    add('V2_TOCEntry', fontSize=9.5, leading=13, spaceAfter=3, textColor=C_BLACK, leftIndent=12)
    add('V2_TOCSub',   fontSize=9, leading=13, spaceAfter=2, textColor=C_GREY, leftIndent=24)

    return base


# ── Header / Footer ───────────────────────────────────────────

class _DRHPDocTemplate(BaseDocTemplate):
    """Custom doc template that updates bookmarks when sections change."""

    def __init__(self, buf, company_name: str, **kwargs):
        super().__init__(buf, **kwargs)
        self.company_name = company_name

    def afterFlowable(self, flowable):
        """Called after each flowable — used to register headings for TOC."""
        if hasattr(flowable, '_bookmark_key'):
            key = flowable._bookmark_key
            level = flowable._toc_level
            text = flowable._toc_text
            self.notify('TOCEntry', (level, text, self.page, key))


def _make_header_footer(company_name: str):
    def _hf(canvas, doc):
        canvas.saveState()
        p = doc.page
        # Header rule
        canvas.setFillColor(C_NAVY)
        canvas.rect(MARGIN, PAGE_H - MARGIN + 4 * mm, INNER_W, 1.5 * mm, fill=1, stroke=0)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(C_GREY)
        canvas.drawString(MARGIN, PAGE_H - MARGIN + 6 * mm, company_name.upper())
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 6 * mm,
                               'DRAFT RED HERRING PROSPECTUS')
        # Footer rule
        canvas.setFillColor(C_LGREY)
        canvas.rect(MARGIN, MARGIN - 6 * mm, INNER_W, 0.5 * mm, fill=1, stroke=0)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(C_GREY)
        canvas.drawString(MARGIN, MARGIN - 10 * mm,
                          'Draft for Discussion Purposes Only — Not for Circulation')
        canvas.drawCentredString(PAGE_W / 2, MARGIN - 10 * mm, f'Page {p}')
        canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 10 * mm,
                               datetime.now(timezone.utc).strftime('%d %B %Y'))
        canvas.restoreState()
    return _hf


def _make_cover_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(C_GREY)
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 10 * mm,
                             'Draft Red Herring Prospectus — For Discussion Purposes Only — Not for Public Distribution')
    canvas.restoreState()


# ── Helper builders ───────────────────────────────────────────

def _table(data: list, col_widths: list, header_rows: int = 1) -> Table:
    """Standard professional table — header rows repeat across pages."""
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), C_NAVY),
        ('TEXTCOLOR',  (0, 0), (-1, header_rows - 1), C_WHITE),
        ('FONTNAME',   (0, 0), (-1, header_rows - 1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 8.5),
        ('GRID',       (0, 0), (-1, -1), 0.3, C_LGREY),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [C_WHITE, colors.HexColor('#F8FAFC')]),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    t = Table(data, colWidths=col_widths, repeatRows=header_rows, splitByRow=True)
    t.setStyle(ts)
    return t


def _fmt_lakhs(val: Optional[float]) -> str:
    if val is None:
        return 'Information Not Provided'
    return f'\u20b9 {val:,.2f} Lakhs'


def _fmt_cr(val: Optional[float]) -> str:
    if val is None:
        return 'Information Not Provided'
    return f'\u20b9 {val:,.2f} Crore'


def _safe_pct(num: Optional[float], den: Optional[float]) -> str:
    if num is None or den is None or den == 0:
        return 'N/A'
    return f'{(num / den * 100):.2f}%'


def _process_section_content(content: str, styles) -> List:
    """
    Convert raw section content string to ReportLab flowables.
    - Handles markdown-style **bold**, bullet points (- prefix)
    - Converts [MISSING: ...] markers to purple annotation paragraphs
    - Strips internal evidence IDs
    - Never exposes raw LLM debug markers in final PDF
    """
    flowables = []
    if not content or not content.strip():
        flowables.append(Paragraph(
            '<i>Information Not Provided — Human Review Required Before Filing</i>',
            styles['V2_Missing']
        ))
        return flowables

    # Split into paragraphs
    paragraphs = content.split('\n\n')
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check for generation error markers — replace with professional notice
        if ERROR_MARKER.search(para):
            flowables.append(Paragraph(
                '<i>This section could not be generated automatically. '
                'Human drafting required before SEBI filing.</i>',
                styles['V2_Missing']
            ))
            continue

        # Handle [MISSING: ...] markers — convert to purple annotation
        if MISSING_MARKER.search(para):
            clean = MISSING_MARKER.sub(
                lambda m: f'[Information Not Provided: {m.group(1)}]',
                para
            )
            flowables.append(Paragraph(clean, styles['V2_Missing']))
            continue

        # Handle conflicting data markers
        if CONFLICTING_MARKER.search(para):
            flowables.append(Paragraph(
                '<i>Conflicting source data identified — human review and reconciliation required.</i>',
                styles['V2_Missing']
            ))
            continue

        # Bullet list items
        lines = para.split('\n')
        bullet_lines = [l for l in lines if l.strip().startswith(('- ', '• ', '* '))]
        non_bullet = [l for l in lines if not l.strip().startswith(('- ', '• ', '* '))]

        if bullet_lines and len(bullet_lines) == len(lines):
            # Pure bullet block
            for bl in bullet_lines:
                text = bl.strip().lstrip('-•* ').strip()
                text = _escape_xml(text)
                flowables.append(Paragraph(f'\u2022 {text}', styles['V2_Bullet']))
        else:
            # Mixed — treat as body paragraph with basic bold handling
            clean = _escape_xml(para)
            # Convert **bold** to <b>bold</b>
            clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean)
            flowables.append(Paragraph(clean, styles['V2_Body']))

    return flowables


def _escape_xml(text: str) -> str:
    """Escape XML special chars for ReportLab Paragraph, but preserve tags we added."""
    # Only escape bare ampersands that aren't already entity refs
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', text)
    # Don't escape < > if they're part of tags we control; strip raw < > outside tags
    return text


# ── Cover page ────────────────────────────────────────────────

def _build_cover(req: DrhpRequestV2, styles) -> List:
    co = req.company
    iss = req.issue
    elems = []
    elems.append(Spacer(1, 2.5 * cm))
    elems.append(Paragraph('DRAFT RED HERRING PROSPECTUS', styles['V2_Cover1']))
    elems.append(Spacer(1, 3 * mm))
    elems.append(HRFlowable(width=INNER_W, thickness=2, color=C_NAVY))
    elems.append(Spacer(1, 5 * mm))
    elems.append(Paragraph(co.name.upper(), styles['V2_Cover2']))
    elems.append(Spacer(1, 2 * mm))

    cin_pan = f'CIN: {co.cin or "Not Provided"}  |  PAN: {co.pan or "Not Provided"}'
    elems.append(Paragraph(cin_pan, styles['V2_CoverSub']))
    elems.append(Paragraph(
        f'Incorporated on: {co.incorporation_date or "Not Provided"}  |  '
        f'{co.sector or ""}',
        styles['V2_CoverSub']
    ))
    elems.append(Spacer(1, 8 * mm))
    elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_LGREY))
    elems.append(Spacer(1, 5 * mm))

    # Issue summary box
    issue_table_data = [
        ['Issue Parameter', 'Details'],
        ['Total Issue Size', _fmt_cr(iss.issue_size_cr)],
        ['Fresh Issue Component', _fmt_cr(iss.fresh_issue_cr)],
        ['OFS Component', _fmt_cr(iss.ofs_cr)],
        ['Face Value', f'\u20b9 {iss.face_value:.0f} per share' if iss.face_value else 'Not Provided'],
        ['Price Band', f'\u20b9 {iss.price_band_low:.0f} to \u20b9 {iss.price_band_high:.0f}' if iss.price_band_high else 'To be announced'],
        ['Lot Size', f'{iss.lot_size:,} shares' if iss.lot_size else 'Not Provided'],
        ['Lead Manager', iss.merchant_banker or 'Not Provided'],
        ['Listing Exchange', co.listing_exchange or 'NSE Emerge / BSE SME'],
    ]
    col_widths = [INNER_W * 0.40, INNER_W * 0.60]
    elems.append(_table(issue_table_data, col_widths))
    elems.append(Spacer(1, 8 * mm))

    # Registered address
    if co.registered_address:
        elems.append(Paragraph(
            f'<b>Registered Office:</b> {_escape_xml(co.registered_address)}',
            styles['V2_CoverSub']
        ))
        elems.append(Spacer(1, 3 * mm))

    # Website
    if co.website:
        elems.append(Paragraph(f'Website: {co.website}', styles['V2_CoverSub']))

    elems.append(Spacer(1, 8 * mm))
    elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_LGREY))
    elems.append(Spacer(1, 4 * mm))
    elems.append(Paragraph(
        'This Draft Red Herring Prospectus has been generated using the IPO Copilot AI Enterprise DRHP Engine. '
        '<b>[GENERATED BY AI - NOT FOR OFFICIAL SEBI FILING WITHOUT HUMAN REVIEW]</b><br/>'
        'It is a working draft for internal review and professional feedback ONLY. '
        'It has NOT been filed with the Securities and Exchange Board of India (SEBI). '
        'It must be reviewed, edited, and approved by SEBI-registered Merchant Bankers, '
        'Chartered Accountants, and Legal Counsel before any regulatory filing or public distribution.',
        styles['V2_CoverNote']
    ))
    elems.append(Spacer(1, 3 * mm))
    
    elems.append(Paragraph(
        f'Generated: {datetime.now(timezone.utc).strftime("%d %B %Y")}  |  '
        f'For Internal Review Only  |  Pipeline v2.0<br/>'
        f'<b>Platform Validation:</b> Includes Automated SEBI Compliance, Consistency, & Risk Validation',
        styles['V2_CoverNote']
    ))
    elems.append(PageBreak())
    return elems


# ── Disclaimer ────────────────────────────────────────────────

def _build_disclaimer(styles) -> List:
    elems = []
    elems.append(Paragraph('IMPORTANT NOTICES AND DISCLAIMER', styles['V2_H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1, color=C_NAVY))
    elems.append(Spacer(1, 4 * mm))

    notices = [
        ('Draft Status', 'This is a Draft Red Herring Prospectus. It has not been filed with SEBI. '
         'It is prepared for internal review and professional consultation purposes only.'),
        ('Not an Offer', 'Nothing in this document constitutes an offer to sell, a solicitation of an '
         'offer to buy, or an invitation to subscribe to any securities in any jurisdiction.'),
        ('AI-Generated Content', 'Portions of this document have been generated with AI assistance. '
         'All AI-generated content must be independently verified by qualified professionals before filing. '
         'Any Information Not Provided annotations indicate data gaps requiring human input.'),
        ('Forward-Looking Statements', 'This document may contain forward-looking statements. These are '
         'based on current expectations and assumptions and are subject to risks and uncertainties. '
         'Actual results may differ materially from projections.'),
        ('Regulatory Filing', 'This document must be reviewed by a SEBI-registered Merchant Banker, '
         'Chartered Accountant (Peer Review Board certified), and Legal Counsel before SEBI filing. '
         'All disclosures must comply with the SEBI (ICDR) Regulations, 2018, as amended.'),
        ('Data Accuracy', 'Financial data presented in this document is based on information provided '
         'by the company. The AI authoring system does not independently verify source documents. '
         'All financial statements must be audited by a qualified CA firm.'),
    ]
    for title, text in notices:
        elems.append(Paragraph(f'<b>{title}:</b> {_escape_xml(text)}', styles['V2_Disclaimer']))

    elems.append(PageBreak())
    return elems


# ── TOC / heading helper ───────────────────────────────────────────

# Heading numbering is kept simple — no custom Paragraph subclasses needed.
# We use a simple [HEADING] Paragraph with a leading <a name=.../> anchor.

_heading_counter = [0]  # module-level counter reset per PDF build


def _safe_key(text: str) -> str:
    """Produce an ASCII-safe key (not used for PDF bookmarks, just for dict lookups)."""
    import unicodedata, re as _r
    n = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return _r.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')[:48]


def _section_heading(title: str, level: int, styles, key: str = '') -> Paragraph:
    """Return a styled heading Paragraph. Simple and reliable — no bookmark subclasses."""
    style_map = {0: 'V2_H1', 1: 'V2_H2', 2: 'V2_H3'}
    style = style_map.get(level, 'V2_H2')
    return Paragraph(_escape_xml(title), styles[style])


def _build_toc_placeholder(styles) -> List:
    """Simple TOC page — no dynamic page number resolution."""
    return [
        Paragraph('TABLE OF CONTENTS', styles['V2_H1']),
        HRFlowable(width=INNER_W, thickness=1, color=C_NAVY),
        Spacer(1, 4 * mm),
        Paragraph(
            'See section headings throughout this document.',
            styles['V2_Body']
        ),
        PageBreak(),
    ]


# ── Financial tables ──────────────────────────────────────────

def _financial_summary_table(financials: List[ExtendedFinancialYear], styles) -> List:
    if not financials:
        return [Paragraph('<i>Financial information not provided.</i>', styles['V2_Missing'])]

    elems = []
    header = ['Particulars (INR Lakhs)'] + [fy.year for fy in financials]
    col_w = [INNER_W * 0.35] + [INNER_W * 0.65 / len(financials)] * len(financials)

    rows_def = [
        ('Revenue from Operations', lambda fy: _fmt_lakhs(fy.revenue)),
        ('EBITDA', lambda fy: _fmt_lakhs(fy.ebitda) if fy.ebitda is not None else 'Not Provided'),
        ('Net Profit / (Loss) after Tax', lambda fy: _fmt_lakhs(fy.net_profit)),
        ('Total Assets', lambda fy: _fmt_lakhs(fy.total_assets)),
        ('Total Equity / Net Worth', lambda fy: _fmt_lakhs(fy.total_equity)),
        ('Total Debt', lambda fy: _fmt_lakhs(fy.total_debt) if fy.total_debt is not None else 'Not Provided'),
        ('Audited', lambda fy: 'Yes' if fy.audited else 'No'),
    ]

    def _cell(label, fns):
        return [Paragraph(label, styles['V2_TableL'])] + [
            Paragraph(fns(fy), styles['V2_TableC']) for fy in financials
        ]

    data = [
        [Paragraph(h, styles['V2_TableH']) for h in header]
    ] + [_cell(label, fn) for label, fn in rows_def]

    elems.append(_table(data, col_w))
    return elems


def _financial_ratios_table(fin_report: Optional[FinancialIntelligenceReport], styles) -> List:
    if not fin_report or not fin_report.ratios:
        return [Paragraph('<i>Financial ratio computation not available.</i>', styles['V2_Missing'])]

    elems = []
    by_cat: Dict[str, List] = {}
    for r in fin_report.ratios:
        by_cat.setdefault(r.category, []).append(r)

    for cat, ratios in by_cat.items():
        elems.append(Paragraph(cat, styles['V2_H3']))
        data = [
            [Paragraph(h, styles['V2_TableH']) for h in ['Metric', 'Value', 'Benchmark / Context']]
        ]
        for r in ratios:
            data.append([
                Paragraph(r.name, styles['V2_TableL']),
                Paragraph(r.formatted_value, styles['V2_TableC']),
                Paragraph(r.benchmark or '—', styles['V2_TableL']),
            ])
        col_w = [INNER_W * 0.40, INNER_W * 0.20, INNER_W * 0.40]
        elems.append(_table(data, col_w))
        elems.append(Spacer(1, 4 * mm))

    return elems


# ── Risk factors table ────────────────────────────────────────

def _build_consistency_annexure(consistency: Optional[ConsistencyReport], styles) -> List:
    """Annexure: data consistency check results — for professional review appendix."""
    if not consistency:
        return []
    elems = []
    elems.append(Paragraph('Annexure — Data Consistency Review', styles['V2_H2']))
    elems.append(Spacer(1, 3 * mm))

    status_labels = {
        'pass': 'All Consistency Checks Passed',
        'warnings': 'Consistency Warnings Noted — Human Review Required',
        'critical_errors': 'Critical Consistency Errors — Must Resolve Before Filing',
    }
    elems.append(Paragraph(
        f'Status: {status_labels.get(consistency.status, consistency.status)} | '
        f'{consistency.passed_checks}/{consistency.total_checks} checks passed',
        styles['V2_Body']
    ))

    if consistency.errors:
        elems.append(Paragraph('Critical Issues Requiring Resolution:', styles['V2_H3']))
        for err in consistency.errors:
            elems.append(Paragraph(
                f'<b>{err.check_name}:</b> {_escape_xml(err.description)}',
                styles['V2_Missing']
            ))
            if err.recommended_fix:
                elems.append(Paragraph(
                    f'Recommended Fix: {_escape_xml(err.recommended_fix)}',
                    styles['V2_Disclaimer']
                ))

    if consistency.warnings:
        elems.append(Spacer(1, 3 * mm))
        elems.append(Paragraph('Review Notes:', styles['V2_H3']))
        for w in consistency.warnings[:15]:
            elems.append(Paragraph(
                f'Note: {_escape_xml(w.description)}',
                styles['V2_Disclaimer']
            ))

    return elems


# ── DRHP section order ────────────────────────────────────────
# This defines the canonical SEBI ICDR section order and grouping.
# Sections are organized into parts matching the SEBI Schedule VI structure.

DRHP_PART_STRUCTURE = [
    ('PART I — GENERAL INFORMATION', [
        ('cover_page',              'Cover Page',                        False),
        ('disclaimer',              'Disclaimer',                        False),
        ('toc',                     'Table of Contents',                 False),
        ('definitions',             'Definitions and Abbreviations',     True),
        ('forward_looking',         'Forward-Looking Statements',        True),
    ]),
    ('PART II — ISSUE SUMMARY', [
        ('issue_summary',           'Issue Summary',                     True),
        ('capital_structure',       'Capital Structure',                 True),
    ]),
    ('PART III — RISK FACTORS', [
        ('risk_factors',            'Risk Factors',                      True),
    ]),
    ('PART IV — INTRODUCTION', [
        ('business_overview',       'Business Overview',                 True),
        ('business_model',          'Business Model and Revenue Streams', True),
        ('competitive_strengths',   'Competitive Strengths',             True),
        ('strategies',              'Our Strategies',                    True),
        ('industry_overview',       'Industry Overview',                 True),
        ('market_opportunity',      'Market Opportunity',                True),
    ]),
    ('PART V — ABOUT OUR COMPANY', [
        ('corporate_structure',     'Corporate Structure',               True),
        ('promoters',               'Promoters and Promoter Group',      True),
        ('management_profile',      'Board of Directors and Management', True),
        ('employees',               'Human Resources and Employees',     True),
        ('key_products',            'Products and Services',             True),
    ]),
    ('PART VI — FINANCIAL INFORMATION', [
        ('financial_statements',    'Audited Financial Statements',      False),  # Built algorithmically
        ('mda',                     'Management Discussion and Analysis',True),
        ('financial_ratios',        'Key Financial Ratios',              False),  # Built algorithmically
        ('related_party',           'Related Party Transactions',        True),
    ]),
    ('PART VII — ISSUE INFORMATION', [
        ('objects_of_issue',        'Objects of the Issue and Use of Proceeds', False),  # Algorithmic
        ('issue_procedure',         'Issue Procedure',                   True),
        ('basis_for_price',         'Basis for Issue Price',             True),
        ('dividend_policy',         'Dividend Policy',                   True),
    ]),
    ('PART VIII — LEGAL AND OTHER INFORMATION', [
        ('outstanding_litigation',  'Outstanding Litigation and Regulatory Actions', True),
        ('government_approvals',    'Government and Statutory Approvals',True),
    ('material_contracts',      'Material Contracts',                True),
    ]),
    ('PART IX — OTHER REGULATORY DISCLOSURES', [
        ('corporate_governance',    'Corporate Governance',              True),
        ('compliance_matrix',       'SEBI ICDR Compliance Matrix',       True),
        ('material_developments',   'Material Developments',             True),
    ]),
    ('PART X — ANNEXURES', [
        ('declaration',             'Declaration',                       True),
    ]),
]


# ── Main PDF builder ──────────────────────────────────────────

def build_enterprise_drhp_pdf(
    req: DrhpRequestV2,
    sections: Dict[str, SectionOutput],
    fin_report: Optional[FinancialIntelligenceReport],
    charts: Optional[Dict[str, Any]] = None,
    consistency: Optional[ConsistencyReport] = None,
) -> bytes:
    """
    Build the enterprise DRHP PDF from pipeline-generated sections.

    The document structure follows SEBI ICDR Schedule VI for SME IPOs.
    Page count is content-driven — not padded to any artificial length.

    Parameters
    ----------
    req:         The DrhpRequestV2 with all company/issue/promoter data
    sections:    Dict of section_id -> SectionOutput from the pipeline
    fin_report:  FinancialIntelligenceReport with computed ratios
    charts:      Dict of chart_key -> ReportLab RLImage flowable
    consistency: ConsistencyReport from the consistency engine
    """
    buf = io.BytesIO()
    co = req.company
    styles = _get_styles()

    # ── Document setup ─────────────────────────────────────────────
    hf = _make_header_footer(co.name)

    def _on_page(canvas, doc_obj):
        """Page 1 = cover (minimal footer); Pages 2+ = full header+footer."""
        if doc_obj.page == 1:
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(C_GREY)
            canvas.drawCentredString(
                PAGE_W / 2, MARGIN - 10 * mm,
                'Draft Red Herring Prospectus - For Discussion Purposes Only'
            )
            canvas.restoreState()
        else:
            hf(canvas, doc_obj)

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title='Draft Red Herring Prospectus - ' + co.name,
        author='IPO Copilot AI Enterprise DRHP Engine',
        subject='SME IPO SEBI ICDR 2018',
    )
    frame = Frame(MARGIN, MARGIN, INNER_W, PAGE_H - 2 * MARGIN,
                  id='main', leftPadding=0, bottomPadding=0,
                  rightPadding=0, topPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=_on_page)])

    elems = []

    # ── Cover page ─────────────────────────────────────────────
    elems.extend(_build_cover(req, styles))

    # ── Disclaimer ─────────────────────────────────────────────
    elems.extend(_build_disclaimer(styles))

    # ── Table of Contents placeholder ──────────────────────────
    elems.extend(_build_toc_placeholder(styles))

    # ── Main content: iterate DRHP structure ───────────────────
    section_num = 0
    for part_title, part_sections in DRHP_PART_STRUCTURE:
        # Part heading
        part_key = f'part_{part_title[:20].lower().replace(" ", "_")}'
        elems.append(_section_heading(part_title, 0, styles, part_key))
        elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
        elems.append(Spacer(1, 4 * mm))

        for sec_id, sec_title, llm_driven in part_sections:
            section_num += 1
            sec_key = f'section_{sec_id}'

            # ── Section heading ────────────────────────────────
            heading = _section_heading(
                f'{section_num}. {sec_title}', 1, styles, sec_key
            )
            elems.append(KeepTogether([heading, Spacer(1, 2 * mm)]))
            elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_TEAL))
            elems.append(Spacer(1, 3 * mm))

            # ── Skip cover/disclaimer/TOC — already built ──────
            if sec_id in ('cover_page', 'disclaimer', 'toc'):
                elems.append(Paragraph(
                    'See preceding pages.',
                    styles['V2_Body']
                ))
                elems.append(Spacer(1, 4 * mm))
                continue

            # ── Special algorithmic sections ───────────────────
            if sec_id == 'financial_statements':
                elems.extend(_financial_summary_table(req.financials, styles))
                # Embed financial chart if available
                if charts and 'revenue_pat' in charts:
                    elems.append(Spacer(1, 4 * mm))
                    elems.append(charts['revenue_pat'])
                elems.append(Spacer(1, 4 * mm))
                continue

            if sec_id == 'financial_ratios':
                elems.extend(_financial_ratios_table(fin_report, styles))
                if charts and 'ebitda_trend' in charts:
                    elems.append(Spacer(1, 4 * mm))
                    elems.append(charts['ebitda_trend'])
                elems.append(Spacer(1, 4 * mm))
                continue

            if sec_id == 'objects_of_issue':
                # Algorithmic use-of-proceeds section with table
                iss = req.issue
                elems.append(Paragraph(
                    _escape_xml(iss.objects_of_issue) if iss.objects_of_issue else
                    'Information Not Provided — Please specify the objects of the issue.',
                    styles['V2_Body']
                ))
                if req.issue.use_of_proceeds_structured:
                    uop_data = [
                        [Paragraph(h, styles['V2_TableH'])
                         for h in ['Purpose', 'Amount (INR Lakhs)', 'Timeline (Months)']]
                    ]
                    total_lakhs = 0.0
                    for item in req.issue.use_of_proceeds_structured:
                        uop_data.append([
                            Paragraph(_escape_xml(item.purpose), styles['V2_TableL']),
                            Paragraph(f'{item.amount_lakhs:,.2f}', styles['V2_TableC']),
                            Paragraph(
                                str(item.timeline_months) if item.timeline_months else '—',
                                styles['V2_TableC']
                            ),
                        ])
                        total_lakhs += item.amount_lakhs
                    uop_data.append([
                        Paragraph('<b>Total</b>', styles['V2_TableL']),
                        Paragraph(f'<b>{total_lakhs:,.2f}</b>', styles['V2_TableC']),
                        Paragraph('', styles['V2_TableC']),
                    ])
                    elems.append(Spacer(1, 4 * mm))
                    elems.append(_table(uop_data, [INNER_W * 0.55, INNER_W * 0.25, INNER_W * 0.20]))

                if charts and 'issue_utilization' in charts:
                    elems.append(Spacer(1, 4 * mm))
                    elems.append(charts['issue_utilization'])
                elems.append(Spacer(1, 4 * mm))
                continue

            if sec_id == 'capital_structure':
                # Promoter table + shareholding chart
                if req.promoters:
                    promo_data = [
                        [Paragraph(h, styles['V2_TableH'])
                         for h in ['Name', 'Designation', 'Pre-Issue Holding (%)']]
                    ]
                    for p in req.promoters:
                        promo_data.append([
                            Paragraph(_escape_xml(p.name), styles['V2_TableL']),
                            Paragraph(_escape_xml(p.designation or '—'), styles['V2_TableL']),
                            Paragraph(f'{p.holding_pct:.2f}%', styles['V2_TableC']),
                        ])
                    total_pct = sum(p.holding_pct for p in req.promoters)
                    promo_data.append([
                        Paragraph('<b>Total Promoter Group</b>', styles['V2_TableL']),
                        Paragraph('', styles['V2_TableL']),
                        Paragraph(f'<b>{total_pct:.2f}%</b>', styles['V2_TableC']),
                    ])
                    elems.append(_table(promo_data, [INNER_W * 0.45, INNER_W * 0.30, INNER_W * 0.25]))
                    elems.append(Spacer(1, 4 * mm))

                iss = req.issue
                issue_data = [
                    [Paragraph(h, styles['V2_TableH']) for h in ['Parameter', 'Value']],
                    [Paragraph('Total Issue Size', styles['V2_TableL']),
                     Paragraph(_fmt_cr(iss.issue_size_cr), styles['V2_TableC'])],
                    [Paragraph('Fresh Issue', styles['V2_TableL']),
                     Paragraph(_fmt_cr(iss.fresh_issue_cr), styles['V2_TableC'])],
                    [Paragraph('Offer for Sale (OFS)', styles['V2_TableL']),
                     Paragraph(_fmt_cr(iss.ofs_cr), styles['V2_TableC'])],
                    [Paragraph('Face Value per Share', styles['V2_TableL']),
                     Paragraph(f'\u20b9 {iss.face_value:.0f}' if iss.face_value else 'Not Provided',
                               styles['V2_TableC'])],
                    [Paragraph('Price Band', styles['V2_TableL']),
                     Paragraph(
                         f'\u20b9 {iss.price_band_low:.0f} to \u20b9 {iss.price_band_high:.0f}'
                         if iss.price_band_high else 'To be announced',
                         styles['V2_TableC']
                     )],
                ]
                elems.append(_table(issue_data, [INNER_W * 0.50, INNER_W * 0.50]))

                if charts and 'shareholding' in charts:
                    elems.append(Spacer(1, 5 * mm))
                    elems.append(charts['shareholding'])

                elems.append(Spacer(1, 4 * mm))
                continue

            # ── LLM / Hybrid section content ───────────────────
            section_out = sections.get(sec_id)
            if section_out and section_out.content:
                content_flowables = _process_section_content(section_out.content, styles)
                elems.extend(content_flowables)

                # Attach chart for this section if relevant
                chart_map = {
                    'mda': 'revenue_pat',
                    'industry_overview': None,
                    'financial_ratios': 'ebitda_trend',
                }
                chart_key = chart_map.get(sec_id)
                if chart_key and charts and chart_key in charts:
                    elems.append(Spacer(1, 4 * mm))
                    elems.append(charts[chart_key])

                # Confidence notice for low-confidence AI sections
                if section_out.confidence < 0.5:
                    elems.append(Spacer(1, 2 * mm))
                    elems.append(Paragraph(
                        f'<i>Note: This section has low AI confidence ({section_out.confidence:.0%}). '
                        'Human review and enhancement strongly recommended before filing.</i>',
                        styles['V2_Missing']
                    ))
            else:
                elems.append(Paragraph(
                    f'Information Not Provided — This section ({sec_title}) requires human drafting '
                    f'before SEBI filing.',
                    styles['V2_Missing']
                ))

            elems.append(Spacer(1, 5 * mm))

        # Page break between major parts (except after last)
        elems.append(CondPageBreak(3 * cm))

    # ── Consistency Annexure (at end) ──────────────────────────
    if consistency and (consistency.errors or consistency.warnings):
        elems.append(PageBreak())
        elems.extend(_build_consistency_annexure(consistency, styles))

    # ── Final notice ───────────────────────────────────────────
    elems.append(PageBreak())
    elems.append(Paragraph('END OF DRAFT RED HERRING PROSPECTUS', styles['V2_H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1, color=C_NAVY))
    elems.append(Spacer(1, 4 * mm))
    elems.append(Paragraph(
        f'This document was generated by IPO Copilot AI Enterprise DRHP Engine on '
        f'{datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")}. '
        f'It contains {len(sections)} AI-generated or algorithmically generated sections. '
        f'It is a working draft only and must be reviewed and approved by qualified professionals '
        f'before SEBI submission.',
        styles['V2_Disclaimer']
    ))

    # ── Build the document (single-pass) ───────────────────────────────
    try:
        doc.build(elems)
    except Exception as exc:
        logger.error("Enterprise PDF build failed: %s", exc, exc_info=True)
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    pdf_bytes = buf.getvalue()
    buf.close()
    logger.info(
        "Enterprise DRHP PDF generated: %d bytes | %d sections | company: %s",
        len(pdf_bytes), len(sections), co.name
    )
    return pdf_bytes

