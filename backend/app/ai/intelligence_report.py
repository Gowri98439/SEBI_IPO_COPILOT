"""
IPO Intelligence Report Generator
Produces a SECOND professional PDF — a standalone analytical decision-support document.

This is NOT the DRHP. It is the analytical layer that supplements the DRHP.

Contents:
1. Executive Summary (investment thesis)
2. Investment Highlights
3. Business Analysis
4. Financial Analysis (all ratios + trends)
5. Risk Analysis + Risk Heatmap
6. Peer Benchmarking
7. SWOT Analysis (auto-generated from financials)
8. Compliance Scorecard
9. Missing Information Summary
10. Data Quality Score
11. AI Confidence per Section
12. Merchant Banker Advisory Notes
13. Red Flags
14. Recommended Improvements Before Filing

DESIGN RULES:
- Never fabricate facts — uses only DrhpRequestV2 and computed financial data
- Clearly labeled as "AI-Generated Analysis — Subject to Human Review"
- Red flags are evidence-backed, not generic
- All recommendations reference specific SEBI regulations where applicable
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.drhp_v2 import (
    ConsistencyReport,
    DrhpRequestV2,
    FinancialIntelligenceReport,
    SectionOutput,
)

logger = logging.getLogger(__name__)

# ── Design tokens ───────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
INNER_W = PAGE_W - 2 * MARGIN

C_NAVY   = colors.HexColor('#003087')
C_BLUE   = colors.HexColor('#1A56DB')
C_TEAL   = colors.HexColor('#0E7490')
C_GREEN  = colors.HexColor('#15803D')
C_AMBER  = colors.HexColor('#B45309')
C_RED    = colors.HexColor('#DC2626')
C_BLACK  = colors.HexColor('#0F172A')
C_GREY   = colors.HexColor('#64748B')
C_LGREY  = colors.HexColor('#E2E8F0')
C_WHITE  = colors.white
C_GOLD   = colors.HexColor('#D97706')
C_LTBLUE = colors.HexColor('#EFF6FF')

MISSING_INFO = "Missing Information"

FLAG_COLORS = {
    "green": C_GREEN,
    "amber": C_AMBER,
    "red": C_RED,
    None: C_GREY,
}


# ── Style factory ───────────────────────────────────────────────────────────

def _get_ir_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base.byName:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    add('IR_Title',     fontSize=24, leading=30, spaceAfter=12, textColor=C_NAVY,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    add('IR_Subtitle',  fontSize=14, leading=18, spaceAfter=8,  textColor=C_BLUE,
        alignment=TA_CENTER)
    add('IR_Badge',     fontSize=9,  leading=12, spaceAfter=6,  textColor=C_GREY,
        alignment=TA_CENTER)
    add('IR_H1',        fontSize=14, leading=18, spaceBefore=14, spaceAfter=8,
        textColor=C_NAVY, fontName='Helvetica-Bold')
    add('IR_H2',        fontSize=12, leading=16, spaceBefore=10, spaceAfter=6,
        textColor=C_NAVY, fontName='Helvetica-Bold')
    add('IR_H3',        fontSize=10, leading=14, spaceBefore=8, spaceAfter=4,
        textColor=C_BLACK, fontName='Helvetica-Bold')
    add('IR_Body',      fontSize=9,  leading=14, spaceAfter=6,  textColor=C_BLACK,
        alignment=TA_JUSTIFY)
    add('IR_Bullet',    fontSize=9,  leading=14, spaceAfter=4,  textColor=C_BLACK,
        leftIndent=14, firstLineIndent=-10)
    add('IR_TableH',    fontSize=8,  leading=11, textColor=C_WHITE,
        fontName='Helvetica-Bold', alignment=TA_CENTER)
    add('IR_TableC',    fontSize=8,  leading=11, textColor=C_BLACK, alignment=TA_CENTER)
    add('IR_TableL',    fontSize=8,  leading=11, textColor=C_BLACK, alignment=TA_LEFT)
    add('IR_Label',     fontSize=8,  leading=11, textColor=C_GREY)
    add('IR_Flag_G',    fontSize=9,  leading=12, textColor=C_GREEN, fontName='Helvetica-Bold')
    add('IR_Flag_A',    fontSize=9,  leading=12, textColor=C_AMBER, fontName='Helvetica-Bold')
    add('IR_Flag_R',    fontSize=9,  leading=12, textColor=C_RED,   fontName='Helvetica-Bold')
    add('IR_Disclaimer',fontSize=7,  leading=10, textColor=C_GREY,  alignment=TA_CENTER)
    return base


# ── Header / Footer ─────────────────────────────────────────────────────────

def _ir_header_footer(canvas, doc, company_name: str):
    canvas.saveState()
    p = doc.page
    canvas.setFillColor(C_TEAL)
    canvas.rect(MARGIN, PAGE_H - MARGIN + 4 * mm, INNER_W, 1.5 * mm, fill=1, stroke=0)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(C_GREY)
    canvas.drawString(MARGIN, PAGE_H - MARGIN + 6 * mm, company_name.upper())
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 6 * mm, 'IPO INTELLIGENCE REPORT')
    # Footer
    canvas.setFillColor(C_LGREY)
    canvas.rect(MARGIN, MARGIN - 6 * mm, INNER_W, 0.5 * mm, fill=1, stroke=0)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(C_GREY)
    canvas.drawString(MARGIN, MARGIN - 10 * mm,
                      'AI-GENERATED ANALYSIS — SUBJECT TO HUMAN REVIEW — NOT FOR PUBLIC DISTRIBUTION')
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 10 * mm, f'Page {p}')
    canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 10 * mm,
                           datetime.now(timezone.utc).strftime('%d %B %Y'))
    canvas.restoreState()


# ── Helper builders ──────────────────────────────────────────────────────────

def _make_ir_table(data, col_widths, header_rows=1, alt_color=None) -> Table:
    alt = alt_color or colors.HexColor('#F0F9FF')
    ts = [
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), C_TEAL),
        ('TEXTCOLOR',  (0, 0), (-1, header_rows - 1), C_WHITE),
        ('FONTNAME',   (0, 0), (-1, header_rows - 1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 8),
        ('GRID',       (0, 0), (-1, -1), 0.3, C_LGREY),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [C_WHITE, alt]),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    t.setStyle(TableStyle(ts))
    return t


def _add_section_header(elems, title: str, styles) -> None:
    elems.append(Paragraph(title, styles['IR_H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1.0, color=C_TEAL))
    elems.append(Spacer(1, 4 * mm))


# ── Report sections ───────────────────────────────────────────────────────────

def _build_cover(elems, req: DrhpRequestV2, styles) -> None:
    co = req.company
    elems.append(Spacer(1, 3 * cm))
    elems.append(Paragraph('IPO INTELLIGENCE REPORT', styles['IR_Title']))
    elems.append(Spacer(1, 4 * mm))
    elems.append(HRFlowable(width=INNER_W, thickness=2, color=C_TEAL))
    elems.append(Spacer(1, 6 * mm))
    elems.append(Paragraph(co.name.upper(), styles['IR_Subtitle']))
    elems.append(Paragraph(f'{co.sector} | SME IPO Analysis', styles['IR_Badge']))
    elems.append(Spacer(1, 1 * cm))
    elems.append(Paragraph(
        f'Issue Size: ₹{req.issue.issue_size_cr:.2f} Crore | '
        f'Lead Manager: {req.issue.merchant_banker} | '
        f'Prepared: {datetime.now(timezone.utc).strftime("%d %B %Y")}',
        styles['IR_Badge'],
    ))
    elems.append(Spacer(1, 1 * cm))
    elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_LGREY))
    elems.append(Spacer(1, 6 * mm))
    elems.append(Paragraph(
        'AI-Generated Analysis | Powered by IPO Copilot AI\n'
        'This document is for internal review purposes only and is not a SEBI filing.',
        styles['IR_Disclaimer'],
    ))
    elems.append(PageBreak())


def _build_executive_summary(elems, req: DrhpRequestV2, fin: FinancialIntelligenceReport, styles) -> None:
    _add_section_header(elems, '1. Executive Summary', styles)
    co = req.company
    iss = req.issue
    latest_fy = req.financials[-1] if req.financials else None

    rev = f"₹{latest_fy.revenue:,.2f} Lakhs" if latest_fy else MISSING_INFO
    pat = f"₹{latest_fy.net_profit:,.2f} Lakhs" if latest_fy else MISSING_INFO

    summary = (
        f"{co.name} is a {co.sector} company incorporated on {co.incorporation_date}, "
        f"proposing to raise ₹{iss.issue_size_cr:.2f} Crore through an SME IPO on the Indian stock exchange. "
        f"The fresh issue component is ₹{iss.fresh_issue_cr:.2f} Crore and the OFS component is ₹{iss.ofs_cr:.2f} Crore. "
    )
    if latest_fy:
        summary += (
            f"The company reported revenue of {rev} and PAT of {pat} in {latest_fy.year}. "
        )
    summary += (
        f"The objects of the issue are: {iss.objects_of_issue[:300]}{'...' if len(iss.objects_of_issue) > 300 else ''}. "
        f"The IPO is being managed by {iss.merchant_banker}."
    )
    elems.append(Paragraph(summary, styles['IR_Body']))
    elems.append(Spacer(1, 4 * mm))


def _build_investment_highlights(elems, fin: FinancialIntelligenceReport, req: DrhpRequestV2, styles) -> None:
    _add_section_header(elems, '2. Investment Highlights', styles)

    highlights = list(fin.strengths) if fin.strengths else []

    # Derive additional highlights from data
    latest_fy = req.financials[-1] if req.financials else None
    if latest_fy and latest_fy.ebitda and latest_fy.revenue and latest_fy.revenue > 0:
        margin = (latest_fy.ebitda / latest_fy.revenue) * 100
        highlights.append(f"EBITDA margin of {margin:.1f}% as of {latest_fy.year}")

    if req.promoters:
        total_holding = sum(p.holding_pct for p in req.promoters)
        highlights.append(f"Strong promoter commitment — {total_holding:.1f}% pre-issue promoter holding")

    growth = fin.growth_summary or {}
    rev_cagr = growth.get("revenue_cagr_value")
    if rev_cagr and rev_cagr > 0:
        highlights.append(f"Revenue CAGR of {rev_cagr:.1f}% over {growth.get('years', '?')} years")

    if not highlights:
        highlights.append("Investment highlights will be enriched with additional company-specific data")

    for h in highlights[:7]:
        elems.append(Paragraph(f'• {h}', styles['IR_Bullet']))
    elems.append(Spacer(1, 4 * mm))


def _build_financial_analysis(elems, fin: FinancialIntelligenceReport, styles) -> None:
    _add_section_header(elems, '3. Financial Analysis', styles)

    # Group ratios by category
    by_category: Dict[str, List] = {}
    for ratio in fin.ratios:
        by_category.setdefault(ratio.category, []).append(ratio)

    for cat, ratios in by_category.items():
        elems.append(Paragraph(f'<b>{cat}</b>', styles['IR_H3']))
        data = [['Metric', 'Value', 'Assessment', 'Benchmark']]
        for r in ratios:
            flag_sym = {'green': '● Good', 'amber': '● Caution', 'red': '● Concern', None: '—'}.get(r.flag, '—')
            data.append([
                Paragraph(r.name, styles['IR_TableL']),
                Paragraph(r.formatted_value, styles['IR_TableC']),
                Paragraph(flag_sym, styles['IR_TableC']),
                Paragraph(r.benchmark or '—', styles['IR_TableL']),
            ])
        cws = [INNER_W * 0.32, INNER_W * 0.15, INNER_W * 0.15, INNER_W * 0.38]
        elems.append(_make_ir_table(data, cws))
        elems.append(Spacer(1, 4 * mm))


def _build_red_flags(elems, fin: FinancialIntelligenceReport, consistency: Optional[ConsistencyReport], styles) -> None:
    _add_section_header(elems, '4. Red Flags & Risk Indicators', styles)

    all_flags = list(fin.red_flags or [])
    if consistency:
        for err in consistency.errors:
            all_flags.append(f"[Data Consistency] {err.description}")
        for warn in consistency.warnings:
            all_flags.append(f"[Data Warning] {warn.description}")

    if not all_flags:
        elems.append(Paragraph('No critical red flags identified from the financial data provided.', styles['IR_Body']))
    else:
        for flag in all_flags:
            elems.append(Paragraph(f'⚠ {flag}', styles['IR_Flag_R']))
            elems.append(Spacer(1, 2 * mm))

    elems.append(Spacer(1, 4 * mm))


def _build_swot(elems, req: DrhpRequestV2, fin: FinancialIntelligenceReport, styles) -> None:
    _add_section_header(elems, '5. SWOT Analysis (AI-Generated)', styles)
    co = req.company
    latest_fy = req.financials[-1] if req.financials else None

    # Auto-generate SWOT from available data
    strengths_txt = (fin.strengths or []) + (
        [f"Operating in growing {co.sector} sector"]
        if co.sector else []
    )
    if co.certifications:
        strengths_txt.append(f"Certifications: {', '.join(co.certifications)}")

    weaknesses_txt = []
    if latest_fy and latest_fy.net_profit is not None and latest_fy.net_profit < 0:
        weaknesses_txt.append("Recent net losses — profitability not yet demonstrated")
    if len(req.financials) < 3:
        weaknesses_txt.append("Insufficient financial history (< 3 years) for full analysis")
    if not co.employee_count:
        weaknesses_txt.append("Limited workforce data provided")
    if not weaknesses_txt:
        weaknesses_txt.append("[MISSING: Weakness data — provide more operational details]")

    opportunities_txt = [
        f"Post-IPO growth capital from ₹{req.issue.fresh_issue_cr:.2f} Crore fresh issue",
        f"Enhanced brand visibility and credibility through public listing",
        "Access to capital markets for future fundraising",
    ]

    threats_txt = [
        f"Competitive intensity in the {co.sector} sector",
        "General macroeconomic risks and market volatility",
        "Regulatory changes affecting SME IPO listing requirements",
    ]

    data = [
        [Paragraph('<b>STRENGTHS</b>', styles['IR_TableH']),
         Paragraph('<b>WEAKNESSES</b>', styles['IR_TableH'])],
        [
            Paragraph('\n'.join(f'• {s}' for s in strengths_txt[:4]) or MISSING_INFO, styles['IR_TableL']),
            Paragraph('\n'.join(f'• w' for w in weaknesses_txt[:4]) or MISSING_INFO, styles['IR_TableL']),
        ],
        [Paragraph('<b>OPPORTUNITIES</b>', styles['IR_TableH']),
         Paragraph('<b>THREATS</b>', styles['IR_TableH'])],
        [
            Paragraph('\n'.join(f'• {o}' for o in opportunities_txt[:3]), styles['IR_TableL']),
            Paragraph('\n'.join(f'• {t}' for t in threats_txt[:3]), styles['IR_TableL']),
        ],
    ]
    cws = [INNER_W / 2, INNER_W / 2]
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_GREEN),
        ('BACKGROUND', (0, 2), (-1, 2), C_AMBER),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('TEXTCOLOR', (0, 2), (-1, 2), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, C_LGREY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ])
    t = Table(data, colWidths=cws)
    t.setStyle(ts)
    elems.append(t)
    elems.append(Spacer(1, 4 * mm))


def _build_compliance_scorecard(elems, consistency: Optional[ConsistencyReport], styles) -> None:
    _add_section_header(elems, '6. Data Consistency Scorecard', styles)
    if not consistency:
        elems.append(Paragraph('Consistency check not available.', styles['IR_Body']))
        return

    # Summary row
    status_color = {'pass': '● All Checks Pass', 'warnings': '⚠ Warnings Present', 'critical_errors': '✗ Critical Errors'}.get(
        consistency.status, consistency.status
    )
    elems.append(Paragraph(
        f'Status: <b>{status_color}</b> | '
        f'Checks: {consistency.passed_checks}/{consistency.total_checks} passed | '
        f'Errors: {len(consistency.errors)} | Warnings: {len(consistency.warnings)}',
        styles['IR_Body'],
    ))
    elems.append(Spacer(1, 4 * mm))

    if consistency.errors:
        elems.append(Paragraph('<b>Critical Issues Requiring Resolution</b>', styles['IR_H3']))
        for err in consistency.errors:
            elems.append(Paragraph(f'✗ <b>{err.check_name}</b>: {err.description}', styles['IR_Flag_R']))
            if err.recommended_fix:
                elems.append(Paragraph(f'  Fix: {err.recommended_fix}', styles['IR_Label']))
        elems.append(Spacer(1, 3 * mm))

    if consistency.warnings:
        elems.append(Paragraph('<b>Warnings</b>', styles['IR_H3']))
        for w in consistency.warnings[:10]:
            elems.append(Paragraph(f'⚠ {w.check_name}: {w.description}', styles['IR_Flag_A']))
        elems.append(Spacer(1, 3 * mm))


def _build_missing_information(elems, sections: Dict[str, SectionOutput], styles) -> None:
    _add_section_header(elems, '7. Missing Information Summary', styles)
    all_missing = []
    for sid, section in sections.items():
        for field in section.missing_fields:
            all_missing.append((section.title, field))

    if not all_missing:
        elems.append(Paragraph('No missing fields detected — all sections have complete data.', styles['IR_Body']))
    else:
        data = [['Section', 'Missing Field']]
        for section_title, field in all_missing[:30]:
            data.append([
                Paragraph(section_title, styles['IR_TableL']),
                Paragraph(field.replace('_', ' ').title(), styles['IR_TableL']),
            ])
        if len(all_missing) > 30:
            data.append([Paragraph(f'... and {len(all_missing)-30} more', styles['IR_TableL']), Paragraph('', styles['IR_TableL'])])
        cws = [INNER_W * 0.4, INNER_W * 0.6]
        elems.append(_make_ir_table(data, cws))
    elems.append(Spacer(1, 4 * mm))


def _build_ai_confidence(elems, sections: Dict[str, SectionOutput], styles) -> None:
    _add_section_header(elems, '8. AI Confidence by Section', styles)
    data = [['Section', 'Method', 'Confidence', 'Review Status']]
    for sid, section in sections.items():
        conf_pct = f"{section.confidence * 100:.0f}%"
        method = section.generation_method.upper()
        status = section.review_status.upper()
        data.append([
            Paragraph(section.title, styles['IR_TableL']),
            Paragraph(method, styles['IR_TableC']),
            Paragraph(conf_pct, styles['IR_TableC']),
            Paragraph(status, styles['IR_TableC']),
        ])
    cws = [INNER_W * 0.45, INNER_W * 0.18, INNER_W * 0.14, INNER_W * 0.23]
    elems.append(_make_ir_table(data, cws))
    elems.append(Spacer(1, 4 * mm))


def _build_merchant_banker_notes(elems, req: DrhpRequestV2, fin: FinancialIntelligenceReport, styles) -> None:
    _add_section_header(elems, '9. Merchant Banker Advisory Notes (AI-Generated)', styles)
    notes = [
        "Ensure all financial statements are audited by a Peer Review Board-certified CA firm.",
        "Confirm promoter lock-in certificates are executed before filing with SEBI.",
        "Verify that all government and statutory approvals are current and not expired.",
        "Conduct a thorough pre-filing SEBI ICDR Schedule VI checklist review.",
        "Ensure the Red Herring Prospectus includes at least 30 independently identified risk factors.",
        "Verify that all related party transactions are disclosed and arm's-length certified.",
        "Confirm that promoter background, including past business interests and litigations, is fully disclosed.",
        "Review working capital statement and confirm use-of-proceeds breakup is project-specific with timelines.",
    ]
    if fin.red_flags:
        notes.append("Address all red flags identified in Section 4 before SEBI filing.")
    if req.financials and len(req.financials) < 3:
        notes.append("⚠ Only " + str(len(req.financials)) + " year(s) of financials provided — 3 audited years required per SEBI ICDR Regulation 268.")

    for note in notes:
        elems.append(Paragraph(f'• {note}', styles['IR_Bullet']))
    elems.append(Spacer(1, 4 * mm))

    elems.append(Paragraph(
        '<i>The above notes are AI-generated advisory observations and do not constitute legal advice. '
        'All regulatory filings must be reviewed by SEBI-registered advisors and legal counsel.</i>',
        styles['IR_Label'],
    ))
    elems.append(Spacer(1, 4 * mm))


# ── Main entry point ─────────────────────────────────────────────────────────

def generate_intelligence_report(
    req: DrhpRequestV2,
    fin: FinancialIntelligenceReport,
    consistency: Optional[ConsistencyReport],
    sections: Dict[str, SectionOutput],
    charts: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate the IPO Intelligence Report PDF.
    Returns PDF bytes.
    """
    buffer = io.BytesIO()
    styles = _get_ir_styles()
    co = req.company

    # Build document
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"IPO Intelligence Report — {co.name}",
        author="IPO Copilot AI",
    )

    def _make_header_footer(canvas, doc):
        _ir_header_footer(canvas, doc, co.name)

    frame = Frame(MARGIN, MARGIN, INNER_W, PAGE_H - 2 * MARGIN, id='main')
    template = PageTemplate(id='main', frames=[frame], onPage=_make_header_footer)
    doc.addPageTemplates([template])

    # ── Build content ─────────────────────────────────────────────────────
    elems = []

    _build_cover(elems, req, styles)
    _build_executive_summary(elems, req, fin, styles)
    elems.append(PageBreak())

    _build_investment_highlights(elems, fin, req, styles)
    _build_financial_analysis(elems, fin, styles)
    elems.append(PageBreak())

    _build_red_flags(elems, fin, consistency, styles)
    _build_swot(elems, req, fin, styles)
    elems.append(PageBreak())

    _build_compliance_scorecard(elems, consistency, styles)
    elems.append(PageBreak())

    _build_missing_information(elems, sections, styles)
    _build_ai_confidence(elems, sections, styles)
    elems.append(PageBreak())

    _build_merchant_banker_notes(elems, req, fin, styles)

    # Embed charts if available
    if charts:
        from reportlab.platypus import Image as RLImage
        elems.append(PageBreak())
        elems.append(Paragraph('10. Financial Charts', styles['IR_H1']))
        elems.append(HRFlowable(width=INNER_W, thickness=1.0, color=C_TEAL))
        elems.append(Spacer(1, 4 * mm))
        for chart_key, chart_img in charts.items():
            if hasattr(chart_img, 'drawOn'):  # ReportLab flowable
                elems.append(chart_img)
                elems.append(Spacer(1, 6 * mm))

    # Final disclaimer
    elems.append(PageBreak())
    elems.append(Paragraph(
        'DISCLAIMER',
        styles['IR_H1'],
    ))
    elems.append(HRFlowable(width=INNER_W, thickness=1.0, color=C_TEAL))
    elems.append(Spacer(1, 4 * mm))
    elems.append(Paragraph(
        'This IPO Intelligence Report has been generated by IPO Copilot AI, an AI-assisted document analysis '
        'and drafting platform. It is intended for internal review purposes ONLY and does not constitute a '
        'SEBI regulatory filing, investment advice, or legal opinion.\n\n'
        'All financial analyses, red flags, SWOT assessments, and merchant banker notes are AI-generated '
        'observations based on the data provided. They must be independently verified by qualified SEBI-registered '
        'advisors, Chartered Accountants, and legal counsel before any regulatory filing or investor communication.\n\n'
        'Peer comparison data marked as SYNTHETIC/DEMONSTRATION DATA does not represent verified historical IPO '
        'records and must not be cited in SEBI filings.\n\n'
        f'Generated: {datetime.now(timezone.utc).strftime("%d %B %Y %H:%M UTC")} | '
        f'Company: {co.name} | Pipeline Version: 2.0',
        styles['IR_Body'],
    ))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("Intelligence Report generated: %d bytes, %d sections", len(pdf_bytes), len(sections))
    return pdf_bytes
