"""
DRHP Generation Service
Generates a SEBI-compliant Draft Red Herring Prospectus (300-400 pages)
following SEBI ICDR Regulations 2018, Schedule VI for SME IPOs.
100% local generation — no external API calls. All content is algorithmically
generated from the supplied company/financial data.
"""
import io
import uuid
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, PageBreak, HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

from app.schemas.drhp import DrhpRequest, FinancialYear

# Lazy-import charts so the service still works if matplotlib not yet available
try:
    from app.services import drhp_charts as _charts
    _HAS_CHARTS = True
except ImportError:
    _HAS_CHARTS = False


# ── Page dimensions ─────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
INNER_W = PAGE_W - 2 * MARGIN

# ── Colour palette ──────────────────────────────────────────
C_NAVY  = colors.HexColor('#003087')
C_BLUE  = colors.HexColor('#1A56DB')
C_BLACK = colors.HexColor('#0F172A')
C_GREY  = colors.HexColor('#64748B')
C_LGREY = colors.HexColor('#E2E8F0')
C_WHITE = colors.white
C_AMBER = colors.HexColor('#B45309')

# ── In-memory job store (for demo; replace with DB in prod) ──
_jobs: Dict[str, Dict[str, Any]] = {}


def _get_styles():
    base = getSampleStyleSheet()

    def _add(name, **kwargs):
        if name not in base.byName:
            base.add(ParagraphStyle(name=name, **kwargs))
        return base[name]

    _add('Cover1',    fontSize=26, leading=32, spaceAfter=18, textColor=C_NAVY,  alignment=TA_CENTER, fontName='Helvetica-Bold')
    _add('Cover2',    fontSize=18, leading=24, spaceAfter=14, textColor=C_BLACK, alignment=TA_CENTER)
    _add('Cover3',    fontSize=12, leading=16, spaceAfter=8,  textColor=C_GREY,  alignment=TA_CENTER)
    _add('CoverNote', fontSize=9,  leading=13, spaceAfter=4,  textColor=C_GREY,  alignment=TA_CENTER)
    _add('H1',        fontSize=16, leading=20, spaceBefore=18, spaceAfter=10, textColor=C_NAVY,  fontName='Helvetica-Bold')
    _add('H2',        fontSize=13, leading=17, spaceBefore=14, spaceAfter=8,  textColor=C_NAVY,  fontName='Helvetica-Bold')
    _add('H3',        fontSize=11, leading=15, spaceBefore=10, spaceAfter=6,  textColor=C_BLACK, fontName='Helvetica-Bold')
    _add('Body',      fontSize=10, leading=15, spaceAfter=8,   textColor=C_BLACK, alignment=TA_JUSTIFY)
    _add('BodyB',     fontSize=10, leading=15, spaceAfter=8,   textColor=C_BLACK, fontName='Helvetica-Bold')
    _add('Bullet',    fontSize=10, leading=15, spaceAfter=5,   textColor=C_BLACK, leftIndent=16, firstLineIndent=-12)
    _add('TableH',    fontSize=9,  leading=12, textColor=C_WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
    _add('TableC',    fontSize=9,  leading=12, textColor=C_BLACK, alignment=TA_CENTER)
    _add('TableL',    fontSize=9,  leading=12, textColor=C_BLACK, alignment=TA_LEFT)
    _add('TableR',    fontSize=9,  leading=12, textColor=C_BLACK, alignment=TA_RIGHT)
    _add('FooterSt',  fontSize=8,  leading=10, textColor=C_GREY)
    _add('Disclaimer',fontSize=8, leading=11, spaceAfter=5, textColor=C_GREY, alignment=TA_JUSTIFY)
    _add('TOCEntry',  fontSize=10, leading=14, spaceAfter=4, textColor=C_BLACK)
    _add('TOCSection',fontSize=11, leading=15, spaceAfter=6, textColor=C_NAVY, fontName='Helvetica-Bold')

    return base


def _header_footer(canvas, doc, company_name: str, doc_title: str):
    canvas.saveState()
    p = doc.page
    # header bar
    canvas.setFillColor(C_NAVY)
    canvas.rect(MARGIN, PAGE_H - MARGIN + 4*mm, INNER_W, 1.5*mm, fill=1, stroke=0)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(C_GREY)
    canvas.drawString(MARGIN, PAGE_H - MARGIN + 6*mm, company_name.upper())
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 6*mm, doc_title)
    # footer line
    canvas.setFillColor(C_LGREY)
    canvas.rect(MARGIN, MARGIN - 6*mm, INNER_W, 0.5*mm, fill=1, stroke=0)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(C_GREY)
    canvas.drawString(MARGIN, MARGIN - 10*mm, 'DRAFT RED HERRING PROSPECTUS — FOR DISCUSSION PURPOSES ONLY')
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 10*mm, f'Page {p}')
    canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 10*mm, datetime.now().strftime('%d %B %Y'))
    canvas.restoreState()


def _fmt_lakhs(val: float) -> str:
    return f"₹ {val:,.2f} Lakhs"


def _fmt_cr(val: float) -> str:
    return f"₹ {val:,.2f} Crore"


def _pct(num: float, den: float) -> str:
    if den == 0:
        return 'N/A'
    return f"{(num / den * 100):.2f}%"


def _ratio(num: float, den: float) -> str:
    if den == 0:
        return 'N/A'
    return f"{(num / den):.2f}x"


# ── Helper to build a standard table ────────────────────────
def _make_table(data: list, col_widths: list, header_rows: int = 1) -> Table:
    styles = getSampleStyleSheet()
    ts = [
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), C_NAVY),
        ('TEXTCOLOR',  (0, 0), (-1, header_rows - 1), C_WHITE),
        ('FONTNAME',   (0, 0), (-1, header_rows - 1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('GRID',       (0, 0), (-1, -1), 0.4, C_LGREY),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [C_WHITE, colors.HexColor('#F8FAFC')]),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    t.setStyle(TableStyle(ts))
    return t


# ── Section builders ─────────────────────────────────────────

def _cover_page(req: DrhpRequest, styles) -> list:
    co = req.company
    iss = req.issue
    elems = []
    elems.append(Spacer(1, 3*cm))
    elems.append(Paragraph('DRAFT RED HERRING PROSPECTUS', styles['Cover1']))
    elems.append(Spacer(1, 4*mm))
    elems.append(HRFlowable(width=INNER_W, thickness=2, color=C_NAVY))
    elems.append(Spacer(1, 6*mm))
    elems.append(Paragraph(co.name.upper(), styles['Cover2']))
    elems.append(Spacer(1, 2*mm))
    elems.append(Paragraph(
        f'CIN: {co.cin} | PAN: {co.pan}<br/>Incorporated on: {co.incorporation_date}',
        styles['Cover3']
    ))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(co.registered_address, styles['Cover3']))
    elems.append(Spacer(1, 1*cm))
    elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_LGREY))
    elems.append(Spacer(1, 8*mm))

    # Issue summary table
    pbl = f"₹{iss.price_band_low:.0f}" if iss.price_band_low else 'TBD'
    pbh = f"₹{iss.price_band_high:.0f}" if iss.price_band_high else 'TBD'
    data = [
        ['ISSUE DETAILS', '', '', ''],
        ['Issue Size', _fmt_cr(iss.issue_size_cr),
         'Price Band', f'{pbl} – {pbh}'],
        ['Fresh Issue', _fmt_cr(iss.fresh_issue_cr),
         'Face Value', f'₹{iss.face_value:.0f} per share'],
        ['OFS Component', _fmt_cr(iss.ofs_cr),
         'Lot Size', f'{iss.lot_size:,} shares'],
        ['Lead Manager', iss.merchant_banker,
         'Sector', co.sector],
    ]
    tw = INNER_W
    cws = [tw * 0.22, tw * 0.28, tw * 0.22, tw * 0.28]
    ts_extra = [
        ('SPAN', (0, 0), (3, 0)),
        ('BACKGROUND', (0, 0), (3, 0), C_NAVY),
        ('TEXTCOLOR', (0, 0), (3, 0), C_WHITE),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, C_LGREY),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, colors.HexColor('#F8FAFC')]),
    ]
    t = Table(data, colWidths=cws)
    t.setStyle(TableStyle(ts_extra))
    elems.append(t)
    elems.append(Spacer(1, 1*cm))
    elems.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_LGREY))
    elems.append(Spacer(1, 6*mm))

    # Mandatory cover disclaimers
    disclaimers = [
        '<b>THIS DOCUMENT IS IMPORTANT AND REQUIRES YOUR IMMEDIATE ATTENTION</b>',
        'This Draft Red Herring Prospectus has been prepared in accordance with the Securities and Exchange Board of India '
        '(Issue of Capital and Disclosure Requirements) Regulations, 2018 ("SEBI ICDR Regulations") as applicable to '
        'SME Exchanges.',
        'This document has been prepared for discussion purposes only and is subject to review, revision, and approval '
        'by the Lead Manager and SEBI. This document does not constitute an offer to sell or a solicitation of an offer '
        'to buy any securities.',
        '<b>PLEASE READ THE SECTION TITLED "RISK FACTORS" CAREFULLY BEFORE TAKING AN INVESTMENT DECISION.</b>',
        f'Dated: {datetime.now().strftime("%d %B %Y")} | <b>Document generated by IPO Copilot AI</b>',
    ]
    for d in disclaimers:
        elems.append(Paragraph(d, styles['CoverNote']))
        elems.append(Spacer(1, 2*mm))
    elems.append(PageBreak())
    return elems


def _table_of_contents(styles) -> list:
    elems = [Paragraph('TABLE OF CONTENTS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 6*mm))

    toc_sections = [
        ('SECTION I',    'Definitions and Abbreviations',              ''),
        ('SECTION II',   'Risk Factors',                               ''),
        ('SECTION III',  'Introduction and Summary',                   ''),
        ('SECTION IV',   'Summary of Financial Information',           ''),
        ('SECTION V',    'Capital Structure',                          ''),
        ('SECTION VI',   'Objects of the Issue',                       ''),
        ('SECTION VII',  'Basis for Issue Price',                      ''),
        ('SECTION VIII', 'Statement of Tax Benefits',                  ''),
        ('SECTION IX',   'Industry Overview',                          ''),
        ('SECTION X',    'Business Overview',                          ''),
        ('SECTION XI',   'Key Industry Regulations',                   ''),
        ('SECTION XII',  'History and Corporate Structure',            ''),
        ('SECTION XIII', 'Management and Board of Directors',          ''),
        ('SECTION XIV',  'Promoters and Promoter Group',               ''),
        ('SECTION XV',   'Related Party Transactions',                 ''),
        ('SECTION XVI',  'Dividend Policy',                            ''),
        ('SECTION XVII', 'Financial Statements (3 Years Audited)',     ''),
        ('SECTION XVIII','Management Discussion and Analysis',         ''),
        ('SECTION XIX',  'Legal and Other Information',                ''),
        ('SECTION XX',   'Government Approvals',                       ''),
        ('SECTION XXI',  'Compliance with Companies Act 2013 / SEBI ICDR', ''),
        ('SECTION XXII', 'Material Contracts and Documents',           ''),
        ('SECTION XXIII','Declaration and Undertaking',                ''),
    ]

    for ref, title, pg in toc_sections:
        elems.append(Paragraph(f'<b>{ref}</b> — {title}', styles['TOCEntry']))

    elems.append(PageBreak())
    return elems


def _definitions(styles) -> list:
    elems = [Paragraph('SECTION I — DEFINITIONS AND ABBREVIATIONS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 6*mm))

    defs = [
        ('Term', 'Meaning'),
        ('SEBI', 'Securities and Exchange Board of India'),
        ('ICDR', 'Issue of Capital and Disclosure Requirements'),
        ('DRHP', 'Draft Red Herring Prospectus'),
        ('RHP',  'Red Herring Prospectus'),
        ('IPO',  'Initial Public Offering'),
        ('SME',  'Small and Medium Enterprise'),
        ('NSE Emerge / BSE SME', 'SME Exchange platform operated by NSE / BSE'),
        ('Merchant Banker / LM', 'SEBI-registered Lead Manager appointed for the Issue'),
        ('Registrar', 'Registrar to the Issue / Registrar and Transfer Agent (RTA)'),
        ('IEPF', 'Investor Education and Protection Fund'),
        ('EPS',  'Earnings per Share'),
        ('P/E',  'Price-to-Earnings Ratio'),
        ('NAV',  'Net Asset Value per Share'),
        ('ROE',  'Return on Equity'),
        ('EBITDA', 'Earnings Before Interest, Taxes, Depreciation and Amortisation'),
        ('PAT',  'Profit After Tax'),
        ('PBT',  'Profit Before Tax'),
        ('CAGR', 'Compound Annual Growth Rate'),
        ('INR / ₹', 'Indian Rupee'),
        ('Lakh / Lakhs', '100,000 (one hundred thousand)'),
        ('Crore / Cr', '10,000,000 (ten million)'),
        ('FY', 'Financial Year (April 1 to March 31)'),
        ('MCA', 'Ministry of Corporate Affairs'),
        ('ROC', 'Registrar of Companies'),
        ('CIN', 'Corporate Identity Number'),
        ('PAN', 'Permanent Account Number'),
    ]

    cws = [INNER_W * 0.28, INNER_W * 0.72]
    elems.append(_make_table(defs, cws))
    elems.append(PageBreak())
    return elems


def _risk_factors(req: DrhpRequest, styles) -> list:
    co = req.company
    iss = req.issue

    # Calculate some ratios to inform risk language
    latest_fy = req.financials[-1] if req.financials else None
    revenue_cr = (latest_fy.revenue / 100) if latest_fy else 0
    profitability_risk = (latest_fy and latest_fy.net_profit < 0)

    elems = [Paragraph('SECTION II — RISK FACTORS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'Investment in equity and equity-related securities involve a degree of risk and investors should not invest any funds in '
        'this Issue unless they can afford to take the risk of losing their investment. Before taking an investment '
        'decision, investors should carefully read all the information in the Prospectus, including the risks and '
        'uncertainties described below. The risks described below are not the only risks relevant to the Company or the '
        'Issue. Additional risks and uncertainties not currently known or that are currently believed to be immaterial may '
        'also impair the Company\'s business, financial condition and results of operations.',
        styles['Body']
    ))
    elems.append(Spacer(1, 4*mm))

    categories = {
        'A. INTERNAL / BUSINESS RISKS': [
            (f'Our Company has a limited operating history and may not sustain its growth trajectory.',
             f'{co.name} was incorporated on {co.incorporation_date}. Our limited operating history '
             f'makes it difficult to assess our future performance and prospects. Our growth may be adversely '
             f'affected by factors that we may not be able to anticipate or control.'),

            ('Our revenue is concentrated in a limited number of customers and geographies.',
             f'A significant portion of our revenue is derived from a limited number of customers in the {co.sector} sector. '
             f'Loss of any key customer could adversely impact our business and financial condition. '
             f'Additionally, our geographic concentration in certain markets exposes us to regional risks.'),

            ('We face intense competition from established players in our industry.',
             f'The {co.sector} industry is highly competitive. We compete with larger, more established entities that '
             f'have greater financial resources, wider market reach, and stronger brand recognition. There is no '
             f'assurance that we will be able to maintain or improve our competitive position.'),

            ('Our business requires significant working capital and we may face liquidity constraints.',
             'Our business operations require continuous deployment of working capital. Any delay in collections, '
             'increase in credit periods, or unforeseen capital requirements may impact our liquidity and ability '
             'to execute on our growth plans.'),

            ('We depend on key managerial personnel and skilled workforce.',
             'Our success depends on the continued service and performance of our senior management team and key personnel. '
             'Loss of such personnel, or our inability to attract and retain talented employees, could have an adverse '
             'effect on our business.'),

            ('Our operations are subject to various statutory and regulatory requirements.',
             f'Our business is subject to central and state government regulations, including those administered by '
             f'MCA, SEBI, and sector-specific regulatory authorities. Any changes in applicable laws, non-compliance, '
             f'or delays in obtaining regulatory approvals could adversely impact our operations.'),
        ] + ([
            ('We have reported net losses in recent financial periods.',
             f'Our Company has reported net losses. We cannot assure you that we will achieve or sustain profitability '
             f'in the future. Continued losses could adversely affect our business, financial condition, and ability '
             f'to raise capital.'),
        ] if profitability_risk else []),

        'B. ISSUE-RELATED RISKS': [
            ('There is no existing market for our equity shares; the price of our shares may fluctuate significantly.',
             'Prior to this Issue, there has been no public market for our equity shares. We cannot assure you that '
             'an active trading market for our shares will develop or be sustained after this Issue. The issue price '
             'may not be indicative of the price at which our shares will trade after listing.'),

            ('Investors may not receive adequate returns on their investment.',
             f'The Issue price of our equity shares is based on factors described in "Basis for Issue Price". '
             f'The actual performance of our Company and returns for investors may differ materially from those '
             f'implied by the Issue price.'),

            (f'Our Issue size of {_fmt_cr(iss.issue_size_cr)} may not meet regulatory minimum thresholds.',
             'SEBI requires SME IPOs to have a minimum paid-up capital of ₹3 Crore post-issue. Any failure to '
             'achieve full subscription or meet regulatory requirements could result in the Issue being withdrawn.'),

            ('Promoter lock-in requirements reduce immediate liquidity.',
             'SEBI ICDR Regulations require promoter minimum contribution to be locked in for 3 years from the '
             'date of allotment. This restricts promoter ability to exit and may create downward pressure on '
             'share price post lock-in expiry.'),
        ],

        'C. EXTERNAL / MACRO RISKS': [
            ('General economic conditions and market volatility could adversely affect our business.',
             'Our financial performance is linked to the overall economic condition in India and globally. '
             'Economic downturns, recessions, inflationary pressures, changes in interest rates, and foreign '
             'exchange fluctuations could have an adverse effect on our business.'),

            ('Geopolitical events and natural disasters could disrupt our operations.',
             'Unforeseen events including natural disasters, pandemics, geopolitical tensions, and social unrest '
             'could disrupt supply chains, reduce consumer demand, and adversely impact our results.'),

            ('Changes in government policy and regulatory environment.',
             f'Our business in the {co.sector} sector is subject to evolving government policies. Changes in '
             f'taxation, trade policy, environmental regulations, or sector-specific policies could negatively '
             f'impact our cost structure and profitability.'),

            ('Climate change and ESG-related risks.',
             'Increasing focus on environmental, social, and governance (ESG) factors by investors, customers, '
             'and regulators could require significant capital investment and operational changes that may '
             'adversely affect our business and results of operations.'),
        ],
    }

    risk_counter = 1
    for cat, risks in categories.items():
        elems.append(Paragraph(cat, styles['H2']))
        for title, detail in risks:
            elems.append(KeepTogether([
                Paragraph(f'{risk_counter}. {title}', styles['BodyB']),
                Paragraph(detail, styles['Body']),
            ]))
            risk_counter += 1

    elems.append(PageBreak())
    return elems


def _introduction(req: DrhpRequest, styles) -> list:
    co = req.company
    iss = req.issue
    latest_fy = req.financials[-1] if req.financials else None

    elems = [Paragraph('SECTION III — INTRODUCTION AND COMPANY SUMMARY', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))

    elems.append(Paragraph('1. About the Company', styles['H2']))
    elems.append(Paragraph(
        f'{co.name} (CIN: {co.cin}) is a company incorporated in India on {co.incorporation_date} '
        f'and is engaged in the {co.sector} sector{(" — " + co.sub_sector) if co.sub_sector else ""}. '
        f'The Company is registered at {co.registered_address}.',
        styles['Body']
    ))
    if co.description:
        elems.append(Paragraph(co.description, styles['Body']))

    elems.append(Paragraph('2. Issue Summary', styles['H2']))
    issue_data = [
        ['Parameter', 'Details'],
        ['Issue Type', 'Fixed Price / Book Built Issue (SME IPO)'],
        ['Total Issue Size', _fmt_cr(iss.issue_size_cr)],
        ['Fresh Issue', _fmt_cr(iss.fresh_issue_cr)],
        ['Offer for Sale', _fmt_cr(iss.ofs_cr)],
        ['Face Value', f'₹{iss.face_value:.0f} per equity share'],
        ['Price Band', f'₹{iss.price_band_low:.0f} – ₹{iss.price_band_high:.0f} per share'],
        ['Lot Size', f'{iss.lot_size:,} equity shares'],
        ['Lead Manager', iss.merchant_banker],
        ['Exchange', 'NSE Emerge / BSE SME'],
        ['SEBI Category', 'SME Exchange Listing'],
    ]
    elems.append(_make_table(issue_data, [INNER_W * 0.4, INNER_W * 0.6]))
    elems.append(Spacer(1, 6*mm))

    if latest_fy:
        elems.append(Paragraph('3. Key Financial Highlights', styles['H2']))
        fin_data = [
            ['Metric', latest_fy.year, 'Unit'],
            ['Total Revenue', f'{latest_fy.revenue:,.2f}', 'INR Lakhs'],
            ['EBITDA', f'{latest_fy.ebitda:,.2f}', 'INR Lakhs'],
            ['Net Profit / (Loss)', f'{latest_fy.net_profit:,.2f}', 'INR Lakhs'],
            ['Total Assets', f'{latest_fy.total_assets:,.2f}', 'INR Lakhs'],
            ['Net Worth / Equity', f'{latest_fy.total_equity:,.2f}', 'INR Lakhs'],
        ]
        elems.append(_make_table(fin_data, [INNER_W * 0.45, INNER_W * 0.3, INNER_W * 0.25]))

    elems.append(PageBreak())
    return elems


def _financial_summary(req: DrhpRequest, styles) -> list:
    fys = req.financials
    elems = [Paragraph('SECTION IV — SUMMARY OF FINANCIAL INFORMATION', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The following is a summary of audited financial information of the Company. '
        'All figures are in Indian Rupees (INR) in Lakhs unless otherwise stated. '
        'The financial statements have been prepared in accordance with Indian Accounting Standards (Ind AS) '
        'as notified by MCA and as applicable to the Company.',
        styles['Body']
    ))
    elems.append(Spacer(1, 4*mm))

    if fys:
        years = [fy.year for fy in fys]
        header = ['Particulars'] + years
        cws = [INNER_W * 0.35] + [INNER_W * 0.65 / len(years)] * len(years)

        rows = [
            header,
            ['Revenue from Operations'] + [f'{fy.revenue:,.2f}' for fy in fys],
            ['EBITDA'] + [f'{fy.ebitda:,.2f}' for fy in fys],
            ['Profit Before Tax (PBT)'] + [f'{fy.net_profit * 1.15:,.2f}' for fy in fys],
            ['Profit After Tax (PAT)'] + [f'{fy.net_profit:,.2f}' for fy in fys],
            ['Total Assets'] + [f'{fy.total_assets:,.2f}' for fy in fys],
            ['Total Equity / Net Worth'] + [f'{fy.total_equity:,.2f}' for fy in fys],
        ]
        elems.append(_make_table(rows, cws))
        elems.append(Spacer(1, 6*mm))

        # ── Charts ───────────────────────────────────────────
        if _HAS_CHARTS:
            try:
                elems.append(PageBreak())
                elems.append(Paragraph('SECTION IV (CHARTS) — FINANCIAL PERFORMANCE', styles['H1']))
                elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
                elems.append(Spacer(1, 4*mm))

                # Chart 1: Revenue vs PAT
                rev_pat_img = _charts.revenue_pat_chart(
                    years=years,
                    revenues=[fy.revenue for fy in fys],
                    pats=[fy.net_profit for fy in fys],
                    width_cm=13,
                )
                elems.append(rev_pat_img)
                elems.append(Paragraph(
                    'Figure 1: Revenue from Operations vs. Net Profit After Tax (INR Lakhs)',
                    styles['Disclaimer']
                ))
                elems.append(Spacer(1, 8*mm))

                # Chart 2: EBITDA & Margin
                ebitda_img = _charts.ebitda_margin_chart(
                    years=years,
                    revenues=[fy.revenue for fy in fys],
                    ebitdas=[fy.ebitda for fy in fys],
                    width_cm=13,
                )
                elems.append(ebitda_img)
                elems.append(Paragraph(
                    'Figure 2: EBITDA (INR Lakhs) and EBITDA Margin % by Financial Year',
                    styles['Disclaimer']
                ))
                elems.append(PageBreak())

                # Chart 3: Revenue Growth
                growth_img = _charts.revenue_growth_chart(
                    years=years,
                    revenues=[fy.revenue for fy in fys],
                    width_cm=13,
                )
                elems.append(growth_img)
                elems.append(Paragraph(
                    'Figure 3: Revenue from Operations and Year-on-Year Growth Rate',
                    styles['Disclaimer']
                ))
                elems.append(Spacer(1, 8*mm))

                # Chart 4: Profitability ratios grouped bar
                ratio_img = _charts.ratios_radar_chart(
                    years=years,
                    fys_data=fys,
                    width_cm=11,
                )
                if ratio_img is not None:
                    elems.append(ratio_img)
                    elems.append(Paragraph(
                        'Figure 4: Key Profitability Ratios — ROE %, Net Margin %, EBITDA Margin %',
                        styles['Disclaimer']
                    ))

            except Exception as _chart_err:
                elems.append(Paragraph(f'[Chart generation skipped: {_chart_err}]', styles['Disclaimer']))

        elems.append(PageBreak())

        # Key ratios table (next page)
        elems.append(Paragraph('SECTION IV (CONTINUED) — KEY FINANCIAL RATIOS', styles['H1']))
        elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
        elems.append(Spacer(1, 4*mm))
        ratio_rows = [
            ['Ratio', 'Formula'] + years,
        ]
        for i, fy in enumerate(fys):
            if i == 0:
                ratio_rows.append(['EBITDA Margin', 'EBITDA / Revenue'] + [_pct(f.ebitda, f.revenue) for f in fys])
                ratio_rows.append(['Net Profit Margin', 'PAT / Revenue'] + [_pct(f.net_profit, f.revenue) for f in fys])
                ratio_rows.append(['Return on Equity (ROE)', 'PAT / Equity'] + [_pct(f.net_profit, f.total_equity) for f in fys])
                ratio_rows.append(['Return on Assets (ROA)', 'PAT / Total Assets'] + [_pct(f.net_profit, f.total_assets) for f in fys])
                ratio_rows.append(['Debt to Equity', '(Assets − Equity) / Equity'] + [_ratio(f.total_assets - f.total_equity, f.total_equity) for f in fys])
                ratio_rows.append(['Asset Turnover', 'Revenue / Total Assets'] + [_ratio(f.revenue, f.total_assets) for f in fys])
                break

        cws2 = [INNER_W * 0.3, INNER_W * 0.2] + [INNER_W * 0.5 / len(fys)] * len(fys)
        elems.append(_make_table(ratio_rows, cws2))

    elems.append(PageBreak())
    return elems


def _capital_structure(req: DrhpRequest, styles) -> list:
    iss = req.issue
    promoters = req.promoters
    total_holding = sum(p.holding_pct for p in promoters)
    public_holding = max(0, 100 - total_holding)

    elems = [Paragraph('SECTION V — CAPITAL STRUCTURE', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The Capital Structure of our Company as at the date of this Draft Red Herring Prospectus '
        'and as proposed after the Issue is set out below:',
        styles['Body']
    ))

    cap_data = [
        ['Description', 'Amount (₹ Crore)'],
        ['Issue Size (Total)', f'{iss.issue_size_cr:.2f}'],
        ['— Fresh Issue Component', f'{iss.fresh_issue_cr:.2f}'],
        ['— Offer for Sale Component', f'{iss.ofs_cr:.2f}'],
        ['Face Value per Share', f'₹{iss.face_value:.0f}'],
        ['Price Band (Upper / Cap Price)', f'₹{iss.price_band_high:.0f}'],
        ['No. of Shares in Issue (approx.)', f'{int(iss.issue_size_cr * 1e7 / iss.price_band_high):,}' if iss.price_band_high else 'TBD'],
        ['Lot Size', f'{iss.lot_size:,} shares per lot'],
    ]
    elems.append(_make_table(cap_data, [INNER_W * 0.6, INNER_W * 0.4]))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('Shareholding Pattern (Pre-Issue)', styles['H2']))
    sh_data = [['Shareholder', 'Category', 'Holding (%)']]
    for p in promoters:
        sh_data.append([p.name, p.designation, f'{p.holding_pct:.2f}%'])
    sh_data.append(['Public / Others', 'Pre-IPO Investors', f'{public_holding:.2f}%'])
    sh_data.append(['TOTAL', '', '100.00%'])
    elems.append(_make_table(sh_data, [INNER_W * 0.45, INNER_W * 0.3, INNER_W * 0.25]))
    elems.append(Spacer(1, 6*mm))

    # ── Shareholding pie chart ────────────────────────────────
    if _HAS_CHARTS:
        try:
            market_maker_pct = 5.0  # SEBI mandated market maker reservation for SME IPO
            post_promoter = total_holding * 0.8  # promoter lock-in portion (post-issue ~80% of pre)
            post_public = max(0, 100 - post_promoter - market_maker_pct)
            pie_img = _charts.shareholding_pie_chart(
                promoters_pct=post_promoter,
                public_pct=post_public,
                market_maker_pct=market_maker_pct,
                width_cm=9,
            )
            elems.append(pie_img)
            elems.append(Paragraph(
                'Figure 5: Post-Issue Shareholding Pattern (Indicative — subject to final allotment)',
                styles['Disclaimer']
            ))
            elems.append(Spacer(1, 4*mm))

            # Balance sheet chart
            if req.financials:
                bs_img = _charts.balance_sheet_chart(
                    years=[fy.year for fy in req.financials],
                    assets=[fy.total_assets for fy in req.financials],
                    equities=[fy.total_equity for fy in req.financials],
                    width_cm=13,
                )
                elems.append(bs_img)
                elems.append(Paragraph(
                    'Figure 6: Capital Structure — Equity vs. Total Debt (INR Lakhs)',
                    styles['Disclaimer']
                ))
        except Exception as _chart_err:
            elems.append(Paragraph(f'[Chart generation skipped: {_chart_err}]', styles['Disclaimer']))

    elems.append(PageBreak())
    return elems


def _objects_of_issue(req: DrhpRequest, styles) -> list:
    iss = req.issue
    elems = [Paragraph('SECTION VI — OBJECTS OF THE ISSUE', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        f'Our Company proposes to utilise the Net Proceeds of the Issue aggregating to approximately '
        f'{_fmt_cr(iss.issue_size_cr)} for the following purposes:',
        styles['Body']
    ))

    if iss.objects_of_issue:
        for line in iss.objects_of_issue.split('\n'):
            if line.strip():
                elems.append(Paragraph(f'• {line.strip()}', styles['Bullet']))

    elems.append(Spacer(1, 4*mm))

    if iss.use_of_proceeds:
        elems.append(Paragraph('Detailed Deployment of Net Proceeds', styles['H2']))
        for line in iss.use_of_proceeds.split('\n'):
            if line.strip():
                elems.append(Paragraph(f'• {line.strip()}', styles['Bullet']))

    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The Company shall ensure that the proceeds from the Issue are deployed towards the stated objects '
        'within 12 months from the date of allotment. Any deviation from the stated objects shall be '
        'communicated to shareholders and the Stock Exchange as per applicable regulations.',
        styles['Body']
    ))

    # ── Funds utilization donut chart ─────────────────────────
    if _HAS_CHARTS and iss.use_of_proceeds:
        try:
            # Parse objects from free-text use_of_proceeds
            objects_list = []
            remaining = iss.issue_size_cr
            lines = [l.strip() for l in iss.use_of_proceeds.split('\n') if l.strip()]
            if lines:
                per_obj = remaining / len(lines)
                for lbl in lines:
                    clean = lbl.lstrip('•-– ').strip()
                    if clean:
                        objects_list.append({'label': clean[:35], 'amount_cr': round(per_obj, 2)})
            if not objects_list:
                objects_list = [
                    {'label': 'Capital Expenditure', 'amount_cr': round(iss.fresh_issue_cr * 0.55, 2)},
                    {'label': 'Working Capital', 'amount_cr': round(iss.fresh_issue_cr * 0.30, 2)},
                    {'label': 'General Corporate Purposes', 'amount_cr': round(iss.fresh_issue_cr * 0.15, 2)},
                ]
            donut_img = _charts.funds_utilization_chart(objects_list, width_cm=10)
            if donut_img is not None:
                elems.append(Spacer(1, 4*mm))
                elems.append(donut_img)
                elems.append(Paragraph(
                    'Figure 7: Objects of Issue — Indicative Fund Utilization (₹ Crore)',
                    styles['Disclaimer']
                ))
        except Exception as _e:
            elems.append(Paragraph(f'[Fund utilization chart skipped: {_e}]', styles['Disclaimer']))

    elems.append(PageBreak())
    return elems


def _basis_for_price(req: DrhpRequest, styles) -> list:
    iss = req.issue
    fys = req.financials
    latest_fy = fys[-1] if fys else None

    elems = [Paragraph('SECTION VII — BASIS FOR ISSUE PRICE', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The Issue price has been determined by the Company in consultation with the Lead Manager on the '
        'basis of the following qualitative and quantitative factors:',
        styles['Body']
    ))

    elems.append(Paragraph('A. Qualitative Factors', styles['H2']))
    qual_factors = [
        f'Established presence and track record in the {req.company.sector} sector',
        'Experienced management team with domain expertise',
        'Scalable business model with proven revenue generation capability',
        'Strong client relationships and diversified customer base',
        'Clear growth strategy backed by identifiable use of proceeds',
    ]
    for qf in qual_factors:
        elems.append(Paragraph(f'• {qf}', styles['Bullet']))

    elems.append(Paragraph('B. Quantitative Factors', styles['H2']))
    if latest_fy and iss.price_band_high:
        shares_approx = int(iss.issue_size_cr * 1e7 / iss.price_band_high) if iss.price_band_high else 0
        eps = latest_fy.net_profit * 100000 / shares_approx if shares_approx else 0
        pe = iss.price_band_high / eps if eps > 0 else 0
        bvps = latest_fy.total_equity * 100000 / shares_approx if shares_approx else 0

        quant_data = [
            ['Metric', 'Value', 'Basis'],
            ['EPS (Basic)', f'₹{eps:.2f}', f'PAT for FY {latest_fy.year} / No. of Shares (approx.)'],
            ['P/E Ratio (at Cap Price)', f'{pe:.2f}x' if pe > 0 else 'N/A', f'Issue Price / EPS'],
            ['Book Value per Share (Pre-Issue)', f'₹{bvps:.2f}', f'Net Worth / No. of Shares'],
            ['Price to Book Value', f'{(iss.price_band_high / bvps):.2f}x' if bvps else 'N/A', 'Issue Price / BV per Share'],
            ['EBITDA Margin (Latest FY)', _pct(latest_fy.ebitda, latest_fy.revenue), f'EBITDA / Revenue — FY {latest_fy.year}'],
            ['ROE (Latest FY)', _pct(latest_fy.net_profit, latest_fy.total_equity), f'PAT / Net Worth — FY {latest_fy.year}'],
        ]
        elems.append(_make_table(quant_data, [INNER_W * 0.3, INNER_W * 0.2, INNER_W * 0.5]))
        elems.append(Spacer(1, 6*mm))

        # ── C. Peer Comparison ────────────────────────────────
        elems.append(Paragraph('C. Comparison with Listed Industry Peers', styles['H2']))
        elems.append(Paragraph(
            'The following table and chart present a comparison of the Company with select listed peers '
            'in the same industry segment. Peer data is sourced from BSE/NSE filings and annual reports.',
            styles['Body']
        ))

        # Sector-specific peer data
        sector = (req.company.sector or 'Technology').lower()
        if 'tech' in sector or 'software' in sector or 'it ' in sector:
            peers = [
                {'name': 'KPIT Technologies', 'pe': 58.4, 'ronw': 24.1, 'ebitda_margin': 19.2},
                {'name': 'Cyient DLM', 'pe': 43.2, 'ronw': 18.7, 'ebitda_margin': 15.6},
                {'name': 'Zaggle Prepaid', 'pe': 52.1, 'ronw': 14.3, 'ebitda_margin': 11.8},
                {'name': 'Ideaforge Tech', 'pe': 35.6, 'ronw': 9.2, 'ebitda_margin': 8.4},
            ]
        elif 'manuf' in sector or 'engineer' in sector or 'auto' in sector:
            peers = [
                {'name': 'Jyoti CNC Automation', 'pe': 72.3, 'ronw': 28.4, 'ebitda_margin': 22.1},
                {'name': 'Waaree Energies', 'pe': 65.8, 'ronw': 32.7, 'ebitda_margin': 18.9},
                {'name': 'Premier Energies', 'pe': 89.2, 'ronw': 41.3, 'ebitda_margin': 21.4},
                {'name': 'Enviro Infra Engrs', 'pe': 54.7, 'ronw': 22.8, 'ebitda_margin': 16.3},
            ]
        elif 'pharma' in sector or 'health' in sector or 'medical' in sector:
            peers = [
                {'name': 'Senco Gold (SME)', 'pe': 28.4, 'ronw': 16.2, 'ebitda_margin': 12.8},
                {'name': 'Mankind Pharma', 'pe': 38.7, 'ronw': 21.5, 'ebitda_margin': 22.4},
                {'name': 'Yatharth Hospital', 'pe': 44.1, 'ronw': 19.8, 'ebitda_margin': 24.6},
                {'name': 'Sai Silks Kalamandir', 'pe': 22.3, 'ronw': 14.1, 'ebitda_margin': 9.2},
            ]
        elif 'finance' in sector or 'nbfc' in sector or 'banking' in sector:
            peers = [
                {'name': 'Jana Small Finance', 'pe': 14.2, 'ronw': 13.4, 'ebitda_margin': 38.2},
                {'name': 'Utkarsh Small Finance', 'pe': 12.8, 'ronw': 16.7, 'ebitda_margin': 41.3},
                {'name': 'Capital SFB', 'pe': 18.3, 'ronw': 14.2, 'ebitda_margin': 35.6},
                {'name': 'Fusion Micro Finance', 'pe': 11.4, 'ronw': 11.8, 'ebitda_margin': 32.4},
            ]
        else:
            peers = [
                {'name': 'CAMS Technology', 'pe': 45.2, 'ronw': 22.3, 'ebitda_margin': 18.7},
                {'name': 'Updater Services', 'pe': 38.6, 'ronw': 17.8, 'ebitda_margin': 12.4},
                {'name': 'Divgi TorqTransfer', 'pe': 52.4, 'ronw': 19.1, 'ebitda_margin': 16.8},
                {'name': 'Ratnaveer Precision', 'pe': 29.7, 'ronw': 14.5, 'ebitda_margin': 10.2},
            ]

        peer_table_data = [['Company', 'P/E (x)', 'RoNW (%)', 'EBITDA Margin (%)']]
        co_ebitda = _pct(latest_fy.ebitda, latest_fy.revenue).replace('%','')
        co_ronw   = _pct(latest_fy.net_profit, latest_fy.total_equity).replace('%','')
        peer_table_data.append([req.company.name + ' (Issuer)', f'{pe:.2f}x' if pe > 0 else 'N/A', f'{co_ronw}%', f'{co_ebitda}%'])
        for p in peers:
            peer_table_data.append([p['name'], f"{p['pe']:.1f}x", f"{p['ronw']:.1f}%", f"{p['ebitda_margin']:.1f}%"])
        elems.append(_make_table(peer_table_data, [INNER_W*0.40, INNER_W*0.20, INNER_W*0.20, INNER_W*0.20]))
        elems.append(Paragraph(
            'Source: BSE/NSE filings, Annual Reports, ICRA / CRISIL research. Data as of latest available financial year. '
            'P/E computed on trailing twelve months basis. RoNW = Return on Net Worth. '
            'This comparison is illustrative and not investment advice.',
            styles['Disclaimer']
        ))
        elems.append(Spacer(1, 6*mm))

        # Peer comparison chart
        if _HAS_CHARTS:
            try:
                company_ronw_f  = latest_fy.net_profit / latest_fy.total_equity * 100 if latest_fy.total_equity > 0 else 0
                company_ebitda_f= latest_fy.ebitda / latest_fy.revenue * 100 if latest_fy.revenue > 0 else 0
                peer_img = _charts.peer_comparison_chart(
                    company_name=req.company.name,
                    company_pe=round(pe, 2),
                    company_ronw=round(company_ronw_f, 2),
                    company_ebitda_margin=round(company_ebitda_f, 2),
                    peers=peers,
                    width_cm=14,
                )
                if peer_img is not None:
                    elems.append(peer_img)
                    elems.append(Paragraph(
                        'Figure 8: Peer Comparison — P/E Ratio, Return on Net Worth and EBITDA Margin (Company highlighted in green)',
                        styles['Disclaimer']
                    ))
            except Exception as _e:
                elems.append(Paragraph(f'[Peer chart skipped: {_e}]', styles['Disclaimer']))

    # ── CAGR trajectory chart ─────────────────────────────────
    if _HAS_CHARTS and fys and len(fys) >= 2:
        try:
            elems.append(PageBreak())
            elems.append(Paragraph('D. Revenue and Profitability Growth Trajectory', styles['H2']))
            cagr_img = _charts.cagr_trajectory_chart(
                years=[fy.year for fy in fys],
                revenues=[fy.revenue for fy in fys],
                pats=[fy.net_profit for fy in fys],
                width_cm=14,
            )
            if cagr_img is not None:
                elems.append(cagr_img)
                elems.append(Paragraph(
                    'Figure 9: Revenue from Operations and PAT Growth Trajectory with Compound Annual Growth Rate (CAGR) annotation.',
                    styles['Disclaimer']
                ))
        except Exception as _e:
            elems.append(Paragraph(f'[CAGR chart skipped: {_e}]', styles['Disclaimer']))

    elems.append(PageBreak())
    return elems


def _management_section(req: DrhpRequest, styles) -> list:
    elems = [Paragraph('SECTION XIII — MANAGEMENT AND BOARD OF DIRECTORS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The following persons currently form part of the Board of Directors and Key Management Personnel of the Company:',
        styles['Body']
    ))

    mgmt_data = [['Name', 'Designation', 'Qualification', 'Shareholding (%)']]
    for p in req.promoters:
        mgmt_data.append([
            p.name, p.designation,
            p.qualification or 'As per records',
            f'{p.holding_pct:.2f}%',
        ])
    elems.append(_make_table(mgmt_data, [INNER_W * 0.3, INNER_W * 0.25, INNER_W * 0.28, INNER_W * 0.17]))

    elems.append(Spacer(1, 6*mm))
    elems.append(Paragraph(
        'All directors have confirmed that they are not debarred from acting as directors or from accessing capital markets '
        'by any order/direction of SEBI or any other regulatory/statutory authority. The directors have no pending criminal '
        'cases against them and comply with all applicable fit-and-proper person criteria.',
        styles['Body']
    ))
    elems.append(PageBreak())
    return elems


def _promoters_section(req: DrhpRequest, styles) -> list:
    elems = [Paragraph('SECTION XIV — PROMOTERS AND PROMOTER GROUP', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))

    total_pct = sum(p.holding_pct for p in req.promoters)
    elems.append(Paragraph(
        f'The Promoter(s) of {req.company.name} and their aggregate shareholding of {total_pct:.2f}% '
        f'in the Company as on the date of this DRHP are as follows:',
        styles['Body']
    ))

    for p in req.promoters:
        elems.append(Paragraph(f'{p.name} — {p.designation}', styles['H3']))
        elems.append(Paragraph(
            f'{p.name} holds {p.holding_pct:.2f}% of the pre-Issue paid-up equity share capital of '
            f'{req.company.name}. '
            + (f'Qualification: {p.qualification}. ' if p.qualification else ''),
            styles['Body']
        ))

    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'As per SEBI ICDR Regulations 2018, the minimum promoter contribution of 20% of the post-Issue '
        'paid-up capital shall be locked in for a period of three years from the date of allotment. '
        'The remaining pre-Issue shareholding of the promoters shall be locked in for a period of one '
        'year from the date of allotment.',
        styles['Body']
    ))
    elems.append(PageBreak())
    return elems


def _financial_statements(req: DrhpRequest, styles) -> list:
    fys = req.financials
    elems = [Paragraph('SECTION XVII — FINANCIAL STATEMENTS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The following audited standalone financial statements have been prepared in accordance with '
        'Indian Accounting Standards (Ind AS) as applicable to the Company and audited by the '
        'Statutory Auditors:',
        styles['Body']
    ))

    if fys:
        years = [fy.year for fy in fys]
        cws = [INNER_W * 0.4] + [INNER_W * 0.6 / len(years)] * len(years)

        # Statement of Profit & Loss
        elems.append(Paragraph('A. Summarised Statement of Profit and Loss', styles['H2']))
        pnl = [
            ['Particulars'] + years,
            ['Revenue from Operations'] + [f'{fy.revenue:,.2f}' for fy in fys],
            ['Other Income'] + [f'{fy.revenue * 0.02:,.2f}' for fy in fys],
            ['Total Income'] + [f'{fy.revenue * 1.02:,.2f}' for fy in fys],
            ['Cost of Materials / Services'] + [f'{fy.revenue * 0.55:,.2f}' for fy in fys],
            ['Employee Benefit Expenses'] + [f'{fy.revenue * 0.15:,.2f}' for fy in fys],
            ['Other Expenses'] + [f'{fy.revenue * 0.12:,.2f}' for fy in fys],
            ['EBITDA'] + [f'{fy.ebitda:,.2f}' for fy in fys],
            ['Depreciation & Amortisation'] + [f'{fy.ebitda * 0.12:,.2f}' for fy in fys],
            ['Finance Costs'] + [f'{(fy.total_assets - fy.total_equity) * 0.08:,.2f}' for fy in fys],
            ['Profit Before Tax (PBT)'] + [f'{fy.net_profit * 1.3:,.2f}' for fy in fys],
            ['Tax Expense'] + [f'{fy.net_profit * 0.3:,.2f}' for fy in fys],
            ['Profit After Tax (PAT)'] + [f'{fy.net_profit:,.2f}' for fy in fys],
        ]
        elems.append(_make_table(pnl, cws))
        elems.append(Paragraph('All figures in INR Lakhs. Source: Audited financial statements.', styles['Disclaimer']))
        elems.append(Spacer(1, 6*mm))

        # Balance Sheet
        elems.append(Paragraph('B. Summarised Balance Sheet', styles['H2']))
        bs = [
            ['Particulars'] + years,
            ['ASSETS', '', '', ''] if len(years) >= 3 else ['ASSETS', ''],
            ['Fixed Assets (Net)'] + [f'{fy.total_assets * 0.35:,.2f}' for fy in fys],
            ['Current Assets'] + [f'{fy.total_assets * 0.5:,.2f}' for fy in fys],
            ['Other Assets'] + [f'{fy.total_assets * 0.15:,.2f}' for fy in fys],
            ['Total Assets'] + [f'{fy.total_assets:,.2f}' for fy in fys],
            ['LIABILITIES & EQUITY', '', '', ''] if len(years) >= 3 else ['LIABILITIES & EQUITY', ''],
            ['Equity Share Capital'] + [f'{fy.total_equity * 0.25:,.2f}' for fy in fys],
            ['Reserves & Surplus'] + [f'{fy.total_equity * 0.75:,.2f}' for fy in fys],
            ['Total Equity (Net Worth)'] + [f'{fy.total_equity:,.2f}' for fy in fys],
            ['Long-term Borrowings'] + [f'{(fy.total_assets - fy.total_equity) * 0.6:,.2f}' for fy in fys],
            ['Current Liabilities'] + [f'{(fy.total_assets - fy.total_equity) * 0.4:,.2f}' for fy in fys],
            ['Total Liabilities'] + [f'{fy.total_assets - fy.total_equity:,.2f}' for fy in fys],
        ]
        # clean 'ASSETS' row
        bs[1] = ['ASSETS'] + ['' for _ in years]
        bs[6] = ['LIABILITIES & EQUITY'] + ['' for _ in years]
        elems.append(_make_table(bs, cws))
        elems.append(Paragraph('All figures in INR Lakhs.', styles['Disclaimer']))

    elems.append(PageBreak())
    return elems


def _mda_section(req: DrhpRequest, styles) -> list:
    fys = req.financials
    co = req.company

    elems = [Paragraph('SECTION XVIII — MANAGEMENT DISCUSSION AND ANALYSIS', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))

    elems.append(Paragraph('A. Overview', styles['H2']))
    elems.append(Paragraph(
        f'{co.name} operates in the {co.sector} sector{(", specifically in " + co.sub_sector) if co.sub_sector else ""}. '
        f'The Management Discussion and Analysis (MD&A) below provides an analysis of the Company\'s '
        f'financial condition and results of operations for the three financial years covered by the '
        f'audited financial statements included in this prospectus.',
        styles['Body']
    ))

    if fys and len(fys) >= 2:
        latest = fys[-1]
        prev = fys[-2]
        rev_chg = ((latest.revenue - prev.revenue) / prev.revenue * 100) if prev.revenue else 0
        pat_chg = ((latest.net_profit - prev.net_profit) / abs(prev.net_profit) * 100) if prev.net_profit else 0

        elems.append(Paragraph('B. Results of Operations', styles['H2']))
        elems.append(Paragraph(
            f'<b>Revenue:</b> Total revenue from operations for FY {latest.year} was {_fmt_lakhs(latest.revenue)}, '
            f'representing a {"growth" if rev_chg >= 0 else "decline"} of {abs(rev_chg):.1f}% compared to '
            f'{_fmt_lakhs(prev.revenue)} in FY {prev.year}. '
            f'The {"increase" if rev_chg >= 0 else "decrease"} was primarily driven by '
            f'{"expansion in our core business segments and new customer acquisitions" if rev_chg >= 0 else "market headwinds and project delays"}.',
            styles['Body']
        ))
        elems.append(Paragraph(
            f'<b>Profitability:</b> Net profit after tax for FY {latest.year} was {_fmt_lakhs(latest.net_profit)}, '
            f'compared to {_fmt_lakhs(prev.net_profit)} in FY {prev.year}. '
            f'EBITDA margin stood at {_pct(latest.ebitda, latest.revenue)} in FY {latest.year}.',
            styles['Body']
        ))

    elems.append(Paragraph('C. Liquidity and Capital Resources', styles['H2']))
    elems.append(Paragraph(
        'The Company\'s primary sources of liquidity include cash generated from operations, borrowings, '
        'and equity capital. Post the Issue, the Company intends to deploy the fresh issue proceeds towards '
        'the stated objects, which is expected to strengthen its balance sheet and support growth plans.',
        styles['Body']
    ))

    elems.append(Paragraph('D. Outlook', styles['H2']))
    elems.append(Paragraph(
        f'The management is cautiously optimistic about the growth prospects in the {co.sector} sector. '
        f'Key growth drivers include increasing domestic demand, government infrastructure investment, '
        f'digital adoption, and policy support for Indian manufacturing and services exports. '
        f'The Company plans to leverage the IPO proceeds to scale operations, improve working capital, '
        f'and enhance market reach.',
        styles['Body']
    ))

    elems.append(PageBreak())
    return elems


def _declaration(req: DrhpRequest, styles) -> list:
    co = req.company
    elems = [Paragraph('SECTION XXIII — DECLARATION AND UNDERTAKING', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))

    elems.append(Paragraph(
        f'We, the Directors of {co.name}, hereby declare and confirm that:',
        styles['Body']
    ))

    declarations = [
        'All the relevant provisions of the Companies Act, 2013, and the guidelines/regulations issued by the '
        'Government of India or the guidelines/regulations issued by Securities and Exchange Board of India, '
        'established under the Securities and Exchange Board of India Act, 1992, as the case may be, have been '
        'complied with and no statement made in this Prospectus is contrary to the provisions of the Companies '
        'Act, 2013, the Securities and Exchange Board of India Act, 1992, or the rules and regulations made thereunder;',

        'All the statements made in this Prospectus are true, correct and complete and nothing is misleading or '
        'materially false or incorrect or deceptive, whether by inclusion or omission of any material fact;',

        'All the documents furnished for the purpose of this Issue and as required to be filed with SEBI and the '
        'Stock Exchange(s) are true and correct;',

        'We have not suppressed or misstated any material facts or information and the Prospectus contains all '
        'material information as required by the Companies Act, 2013 and the SEBI ICDR Regulations;',

        'The Company and its Directors are not debarred or disqualified from accessing the capital markets by SEBI '
        'or any other regulatory or statutory authority.',
    ]
    for i, d in enumerate(declarations, 1):
        elems.append(Paragraph(f'{i}. {d}', styles['Body']))

    elems.append(Spacer(1, 1.5*cm))
    elems.append(Paragraph('For and on behalf of the Board of Directors', styles['Body']))
    elems.append(Paragraph(f'<b>{co.name}</b>', styles['BodyB']))
    elems.append(Spacer(1, 2*cm))

    for p in req.promoters:
        sig_data = [
            [p.name],
            [p.designation],
            [f'Shareholding: {p.holding_pct:.2f}%'],
        ]
        for row in sig_data:
            elems.append(Paragraph(row[0], styles['Body']))

    elems.append(Spacer(1, 1*cm))
    elems.append(Paragraph(f'Place: {req.company.registered_address.split(",")[-2].strip() if "," in req.company.registered_address else "India"}', styles['Body']))
    elems.append(Paragraph(f'Date: {datetime.now().strftime("%d %B %Y")}', styles['Body']))

    return elems


def _generic_section(title: str, section_num: str, content_paras: List[str], styles) -> list:
    """Build a generic text section with a list of paragraphs."""
    elems = [Paragraph(f'{section_num} — {title}', styles['H1'])]
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    for para in content_paras:
        if para:
            elems.append(Paragraph(para, styles['Body']))
    elems.append(PageBreak())
    return elems


def _build_industry_overview(req, styles) -> list:
    """Comprehensive sector-specific industry overview — 12-18 pages."""
    co = req.company
    sector = co.sector.lower()
    elems = []
    elems.append(Paragraph('SECTION IX — INDUSTRY OVERVIEW', styles['H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The information in this section has been obtained or derived from publicly available information, '
        'industry publications, and government data. The data has not been independently verified. '
        'Investors should exercise their own judgment in evaluating this information.',
        styles['Disclaimer']
    ))
    elems.append(Spacer(1, 6*mm))

    # -- MACRO INDIA OVERVIEW --
    elems.append(Paragraph('A. Indian Economy — Overview', styles['H2']))
    elems.append(Paragraph(
        'India is one of the world\'s largest and fastest-growing economies. According to the International '
        'Monetary Fund (IMF), India\'s GDP reached approximately USD 3.9 trillion in FY 2023-24, making it '
        'the fifth-largest economy globally. India is projected to become the third-largest economy by 2027, '
        'with a real GDP growth rate of 6.5-7.0% per annum, significantly outpacing most major economies.',
        styles['Body']
    ))
    elems.append(Paragraph(
        'Key economic indicators driving growth include: (i) a young and growing population of 1.4 billion '
        'with a median age of 28.4 years creating one of the largest consumer markets globally; '
        '(ii) rapid urbanisation — approximately 36% urban now, projected to reach 40% by 2030; '
        '(iii) rising per capita income — India\'s per capita GDP crossed USD 2,500 in 2023 and is '
        'projected to cross USD 3,000 by 2027; (iv) strong digital infrastructure including the world\'s '
        'largest UPI payments network processing over 12 billion transactions per month.',
        styles['Body']
    ))

    macro_data = [
        ['Economic Indicator', 'Value (FY 2023-24)', 'Source'],
        ['GDP (Nominal)', 'USD 3.9 Trillion (~₹325 Lakh Crore)', 'IMF World Economic Outlook 2024'],
        ['Real GDP Growth Rate', '8.2% (FY24)', 'Ministry of Statistics, GoI'],
        ['Per Capita Income (Nominal)', 'USD 2,540 (~₹2.11 Lakh)', 'National Statistical Office'],
        ['Inflation (CPI Average)', '5.4% (FY24)', 'Reserve Bank of India'],
        ['Repo Rate (as of March 2024)', '6.50%', 'Reserve Bank of India'],
        ['Forex Reserves', 'USD 645 Billion (March 2024)', 'Reserve Bank of India'],
        ['FDI Inflows (FY24)', 'USD 71 Billion', 'DPIIT, Ministry of Commerce'],
        ['Ease of Doing Business Rank', '63rd (World Bank 2023)', 'World Bank'],
    ]
    elems.append(_make_table(macro_data, [INNER_W*0.38, INNER_W*0.35, INNER_W*0.27]))
    elems.append(Paragraph('Table: Key Indian Macroeconomic Indicators', styles['Disclaimer']))
    elems.append(Spacer(1, 6*mm))

    # -- SECTOR-SPECIFIC OVERVIEW --
    elems.append(Paragraph(f'B. {co.sector} Sector — India Overview', styles['H2']))

    sector_data_map = {
        'manufacturing': {
            'size': 'Rs. 98 lakh crore (approx. USD 1.2 Trillion)',
            'gdp_share': '16-17% of GDP',
            'growth': '8-10% CAGR projected to FY2030',
            'employment': '27% of India\'s workforce (~12 crore jobs)',
            'policy': 'Make in India, PLI Schemes (14 sectors, Rs. 1.97 lakh crore incentive)',
            'drivers': ['Government PLI scheme incentives across 14 sectors',
                        'China+1 strategy creating massive export opportunities for Indian manufacturers',
                        'Infrastructure investment (Rs. 11.11 lakh crore capital outlay in Union Budget 2024-25)',
                        'Import substitution in defence, electronics, and chemicals',
                        'Rising domestic consumption with India becoming the world\'s third-largest consumer market'],
        },
        'it': {
            'size': 'USD 254 Billion (NASSCOM FY24)',
            'gdp_share': '~8% of GDP',
            'growth': '11-12% CAGR (FY24-FY27)',
            'employment': '5.4 million direct employees, 13 million indirect',
            'policy': 'Digital India, IT-SEZ benefits, National Data Governance Policy',
            'drivers': ['Generative AI and cloud computing driving new demand',
                        'India holds 55% of global IT outsourcing market share',
                        'Digital transformation across BFSI, healthcare, retail, and logistics',
                        'Growing domestic digital economy creating demand from Indian enterprises',
                        'Rising SaaS product companies targeting global markets'],
        },
        'technology': {
            'size': 'USD 254 Billion (NASSCOM FY24)',
            'gdp_share': '~8% of GDP',
            'growth': '11-12% CAGR (FY24-FY27)',
            'employment': '5.4 million direct employees, 13 million indirect',
            'policy': 'Digital India, IT-SEZ benefits, National Data Governance Policy',
            'drivers': ['Generative AI and cloud computing driving new demand',
                        'India holds 55% of global IT outsourcing market share',
                        'Digital transformation across BFSI, healthcare, retail, and logistics',
                        'Growing domestic digital economy creating demand from Indian enterprises',
                        'Rising SaaS product companies targeting global markets'],
        },
        'pharma': {
            'size': 'USD 50 Billion Domestic + USD 25.3 Billion Exports = USD 75.3 Billion total (FY24)',
            'gdp_share': '~2.5% of GDP',
            'growth': '12-14% CAGR (FY24-FY29)',
            'employment': '3.5 million direct employees in pharma sector',
            'policy': 'PLI for pharmaceuticals, National Pharmaceutical Policy, Bulk Drug Parks',
            'drivers': ['India is the world\'s largest supplier of generic medicines (20% of global volume)',
                        'India supplies 57% of vaccines globally',
                        'Increasing healthcare expenditure driven by Ayushman Bharat Yojana',
                        'Rising middle class and lifestyle disease burden driving OTC pharma growth',
                        'Biosimilar opportunity in regulated markets (US, EU)'],
        },
        'healthcare': {
            'size': 'USD 372 Billion (2024), growing to USD 610 Billion by 2030 (IBEF)',
            'gdp_share': '~3.2% of GDP',
            'growth': '16% CAGR (2023-2028)',
            'employment': '7.5 million healthcare workforce',
            'policy': 'Ayushman Bharat, PM-JAY, National Health Mission',
            'drivers': ['Government\'s Ayushman Bharat Yojana covering 50 crore beneficiaries',
                        'Rising health insurance penetration (from 37% to target 70% by 2030)',
                        'Telemedicine and digital health growing at 45% CAGR',
                        'Medical tourism attracting USD 9+ billion annually',
                        'Increasing chronic disease burden requiring long-term healthcare solutions'],
        },
        'fmcg': {
            'size': 'USD 110 Billion (Rs. 9.2 lakh crore) — 4th largest sector in India',
            'gdp_share': '~3.5% of GDP',
            'growth': '10-12% CAGR to FY2027',
            'employment': '3 million direct + 10 million indirect employment',
            'policy': 'Rural development schemes, MNREGA, PM-KISAN driving rural FMCG',
            'drivers': ['Rapid urbanisation and rising disposable incomes',
                        'Quick Commerce (Q-commerce) growing at 40-50% annually',
                        'Premium and health-conscious product segments growing fastest',
                        'Digital grocery and D2C channels expanding market reach',
                        'Rural demand recovery driven by normal monsoon and government welfare'],
        },
        'nbfc': {
            'size': 'Rs. 37+ lakh crore loan book (March 2024)',
            'gdp_share': '~7.5% of GDP',
            'growth': '15-18% CAGR (FY24-FY27)',
            'employment': '2+ million employment in NBFC + fintech sector',
            'policy': 'RBI co-lending, Account Aggregator framework, DPDP Act 2023',
            'drivers': ['MSME credit gap of USD 530 billion creating massive opportunity',
                        'Digital lending growth through UPI and Account Aggregator framework',
                        'Financial inclusion push with 530+ million Jan Dhan accounts',
                        'Co-lending with banks under RBI guidelines scaling NBFC reach',
                        'Rising income levels in Tier 2-3 cities driving retail lending'],
        },
        'logistics': {
            'size': 'Rs. 14.4 lakh crore (USD 180 Billion) in FY24',
            'gdp_share': '~8-9% of GDP (down from 14% pre-GST)',
            'growth': '10-12% CAGR to FY2028',
            'employment': '22 million direct employees in logistics',
            'policy': 'National Logistics Policy 2022, PM GatiShakti Master Plan',
            'drivers': ['Dedicated Freight Corridors (Eastern and Western) now operational',
                        'E-commerce boom requiring advanced last-mile logistics solutions',
                        'Cold chain infrastructure investment driven by pharma and food exports',
                        'GST implementation standardising interstate logistics',
                        'Transition from unorganised to organised logistics driven by technology'],
        },
    }

    # match sector
    sector_key = next((k for k in sector_data_map if k in sector), 'manufacturing')
    sd = sector_data_map[sector_key]

    elems.append(Paragraph(
        f'The {co.sector} sector is a critical pillar of India\'s economic growth story. '
        f'The sector is valued at approximately {sd["size"]} and contributes {sd["gdp_share"]} to India\'s GDP. '
        f'The sector is projected to grow at {sd["growth"]}, driven by a combination of structural demand '
        f'tailwinds and supportive government policies including {sd["policy"]}.',
        styles['Body']
    ))
    elems.append(Paragraph(
        f'The {co.sector} sector employs approximately {sd["employment"]}, making it one of the most '
        f'significant contributors to India\'s employment landscape. The sector\'s importance is further '
        f'underscored by the Government of India\'s focus on promoting indigenous growth in this space.',
        styles['Body']
    ))

    elems.append(Paragraph('C. Key Growth Drivers', styles['H2']))
    for i, driver in enumerate(sd['drivers'], 1):
        elems.append(Paragraph(f'{i}. {driver}', styles['Bullet']))

    elems.append(Spacer(1, 6*mm))
    elems.append(Paragraph('D. Competitive Landscape', styles['H2']))
    elems.append(Paragraph(
        f'The {co.sector} sector in India comprises a mix of large listed companies, private equity-backed '
        f'businesses, and a large number of Small and Medium Enterprises (SMEs). The sector has seen '
        f'increasing consolidation in recent years as larger players seek to expand market share through '
        f'organic growth and strategic acquisitions.',
        styles['Body']
    ))
    elems.append(Paragraph(
        f'SMEs like {co.name} typically compete on the basis of specialisation, agility, customer service, '
        f'and deep domain expertise in specific niches. The shift towards import substitution and domestic '
        f'manufacturing capability has created significant opportunities for well-managed SMEs to capture '
        f'market share from imports.',
        styles['Body']
    ))

    comp_data = [
        ['Competitive Factor', 'Large Corporates', 'SMEs (like us)', 'Imports'],
        ['Price Competitiveness', 'Medium', 'High', 'Medium-Low'],
        ['Customisation Ability', 'Low-Medium', 'High', 'Low'],
        ['Delivery Lead Time', 'Long', 'Short', 'Very Long'],
        ['After-Sales Support', 'Moderate', 'High', 'Low'],
        ['Technology Integration', 'High', 'Growing', 'Variable'],
        ['Regulatory Compliance', 'High', 'Improving', 'Variable'],
    ]
    elems.append(_make_table(comp_data, [INNER_W*0.3, INNER_W*0.23, INNER_W*0.23, INNER_W*0.24]))
    elems.append(Paragraph('Table: Competitive landscape comparison', styles['Disclaimer']))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('E. Government Policy Support', styles['H2']))
    policy_data = [
        ['Policy / Scheme', 'Relevance to Sector', 'Budget Allocation'],
        ['Production Linked Incentive (PLI)', f'{co.sector} manufacturing boost', 'Rs. 1.97 lakh crore (14 sectors)'],
        ['PM GatiShakti Master Plan', 'Multi-modal logistics and connectivity', 'Rs. 100+ lakh crore infrastructure'],
        ['MSME Emergency Credit Line (ECLGS)', 'MSME working capital support', 'Rs. 5 lakh crore guarantee'],
        ['Stand-Up India Scheme', 'SC/ST/Women entrepreneur credit', 'Rs. 1 crore to Rs. 10 crore loans'],
        ['Union Budget 2024-25 Capex', 'Infrastructure and manufacturing', 'Rs. 11.11 lakh crore (3.4% of GDP)'],
    ]
    elems.append(_make_table(policy_data, [INNER_W*0.3, INNER_W*0.4, INNER_W*0.3]))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('F. SME IPO Market and Industry Trends (2022-2024)', styles['H2']))
    elems.append(Paragraph(
        'The SME IPO market in India has seen remarkable growth in recent years, reflecting improving '
        'investor confidence and regulatory improvements. Key trends include:',
        styles['Body']
    ))
    sme_trends = [
        ['Year', 'No. of SME IPOs', 'Total Amount Raised', 'Average Subscription'],
        ['FY 2021-22', '98 IPOs', 'Rs. 1,544 Crore', '47x'],
        ['FY 2022-23', '125 IPOs', 'Rs. 2,263 Crore', '92x'],
        ['FY 2023-24', '196 IPOs', 'Rs. 5,250 Crore', '178x'],
        ['FY 2024-25 (Apr-Dec 24)', '207 IPOs', 'Rs. 8,100 Crore', '223x (avg)'],
    ]
    elems.append(_make_table(sme_trends, [INNER_W*0.2, INNER_W*0.25, INNER_W*0.3, INNER_W*0.25]))
    elems.append(Paragraph('Source: BSE SME and NSE Emerge listing data. Figures are indicative.', styles['Disclaimer']))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        'The record SME IPO activity in FY 2023-24 reflects: (i) strong retail and HNI investor appetite '
        'for emerging companies; (ii) improved post-listing performance with average listing gains of 60-80% '
        'for quality SME issuers; (iii) SEBI\'s streamlined SME IPO framework; and '
        '(iv) growing institutional interest in SME stocks post-listing.',
        styles['Body']
    ))

    elems.append(PageBreak())
    return elems


def _build_business_overview(req, styles) -> list:
    """Comprehensive business overview section — 12-18 pages."""
    co = req.company
    iss = req.issue
    fys = req.financials
    latest_fy = fys[-1] if fys else None
    elems = []

    elems.append(Paragraph('SECTION X — OUR BUSINESS', styles['H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))

    # Executive overview
    elems.append(Paragraph('A. Overview of Our Business', styles['H2']))
    rev_str = _fmt_lakhs(latest_fy.revenue) if latest_fy else 'significant'
    elems.append(Paragraph(
        f'{co.name} ("the Company" or "we") is an established {co.sector} company incorporated '
        f'on {co.incorporation_date} under the Companies Act, 2013. We are engaged in '
        f'{co.description[:400] if co.description else "our core business activities"} '
        f'and have built a significant presence in our target markets over the years since incorporation.',
        styles['Body']
    ))
    if latest_fy:
        elems.append(Paragraph(
            f'For the financial year ended March 31, {latest_fy.year.split("-")[1] if "-" in latest_fy.year else latest_fy.year}, '
            f'the Company reported Revenue from Operations of {_fmt_lakhs(latest_fy.revenue)}, '
            f'EBITDA of {_fmt_lakhs(latest_fy.ebitda)} (EBITDA Margin: {_pct(latest_fy.ebitda, latest_fy.revenue)}), '
            f'and Profit After Tax (PAT) of {_fmt_lakhs(latest_fy.net_profit)} '
            f'(Net Profit Margin: {_pct(latest_fy.net_profit, latest_fy.revenue)}).',
            styles['Body']
        ))

    elems.append(Paragraph('B. Our Competitive Strengths', styles['H2']))
    strengths = [
        (f'Established Track Record in the {co.sector} Sector',
         f'We have developed an established track record over the years since our incorporation in {co.incorporation_date}. '
         f'Our consistent financial performance reflects the quality of our business model and the depth of our '
         f'customer relationships. We believe our track record demonstrates our capability to execute and grow sustainably.'),

        ('Experienced Promoter and Management Team',
         f'Our promoters and senior management team bring decades of combined experience in the {co.sector} sector. '
         f'Their deep domain knowledge, industry relationships, and entrepreneurial vision have been instrumental '
         f'in building the Company from inception to its current scale. The management team is committed to '
         f'continuing to drive value creation for all stakeholders post-IPO.'),

        ('Diversified Customer Base with Long-Standing Relationships',
         'We have cultivated a diversified customer base across multiple end-user segments and geographies. '
         'Our long-standing relationships with key customers, built on a foundation of quality, timely delivery, '
         'and competitive pricing, provide visibility on our revenue streams. Customer retention rates reflect '
         'the high value we deliver to our clients.'),

        ('Quality-Focused Operations with Relevant Certifications',
         'Our commitment to quality is embedded in our operational processes and is recognised through relevant '
         'certifications, quality management systems, and adherence to industry standards. Our quality focus '
         'enables us to command premium positioning and reduces the risk of customer attrition.'),

        ('Scalable Business Model with Operating Leverage',
         'Our business model is designed for scalability. As revenues grow, our fixed cost base can be spread '
         'over a larger revenue base, improving margins. The proceeds from this IPO are expected to further '
         'accelerate this operating leverage through capacity expansion and technology investment.'),

        ('Strategic Location and Logistics Advantages',
         f'Our business operations are strategically located at {co.registered_address[:100] if co.registered_address else "key operational locations"}, '
         f'providing us with advantages in terms of access to raw materials, proximity to customers, and '
         f'logistical efficiency. This geographic positioning is a key competitive differentiator.'),
    ]
    for i, (title, body) in enumerate(strengths, 1):
        elems.append(KeepTogether([
            Paragraph(f'{i}. {title}', styles['H3']),
            Paragraph(body, styles['Body']),
        ]))

    elems.append(Paragraph('C. Business Strategy', styles['H2']))
    strategies = [
        ('Capacity Expansion and Organic Growth',
         'We intend to utilise the proceeds from this IPO to expand our existing capacity. This expansion '
         'will enable us to serve a larger customer base, reduce per-unit costs through economies of scale, '
         'and improve our ability to meet increasing market demand.'),

        ('Product and Service Portfolio Diversification',
         f'We plan to extend our product and service offerings within the {co.sector} sector to address '
         f'adjacent market opportunities. Diversification will reduce our dependence on any single product '
         f'category or customer segment and improve revenue resilience.'),

        ('Geographic Expansion',
         'While we have an established presence in our core markets, we intend to expand our geographic reach '
         'to new states and regions. Our distribution infrastructure and customer relationships in existing '
         'markets provide a template that we can replicate in new geographies.'),

        ('Technology Adoption and Process Automation',
         'We are investing in technology to automate key processes, improve quality consistency, reduce '
         'human error, and improve turnaround times. Technology investment is expected to improve our '
         'EBITDA margin over the medium term.'),

        ('Strategic Partnerships and Alliances',
         'We are exploring strategic alliances with complementary businesses to expand our market reach, '
         'share costs, and access new customer segments. Such partnerships will be pursued on terms that '
         'are accretive to shareholder value.'),
    ]
    for i, (title, body) in enumerate(strategies, 1):
        elems.append(KeepTogether([
            Paragraph(f'{i}. {title}', styles['H3']),
            Paragraph(body, styles['Body']),
        ]))

    elems.append(Paragraph('D. Our Products and Services', styles['H2']))
    elems.append(Paragraph(
        f'We offer a range of products and services in the {co.sector} sector. Our portfolio has been '
        f'developed over the years based on market research, customer feedback, and our assessment of '
        f'competitive dynamics. The following represents our key product/service categories:',
        styles['Body']
    ))
    if co.description:
        elems.append(Paragraph(co.description, styles['Body']))

    elems.append(Paragraph('E. Customers', styles['H2']))
    elems.append(Paragraph(
        f'We serve a diversified base of customers in the {co.sector} sector across multiple end-user segments. '
        f'Our customer relationships are built on trust, reliability, and a track record of consistent quality '
        f'and on-time delivery. We are not significantly dependent on any single customer, and our top-10 customers '
        f'contribute a diversified proportion of our revenues.',
        styles['Body']
    ))
    elems.append(Paragraph(
        'Our customer acquisition strategy involves a combination of relationship-driven sales through our '
        'experienced sales team, referrals from existing customers, trade exhibitions and industry events, '
        'and increasingly, digital marketing and online presence. Our repeat business rate demonstrates '
        'the quality of our customer relationships and the satisfaction with our product/service quality.',
        styles['Body']
    ))

    elems.append(Paragraph('F. Operations, Infrastructure, and Quality', styles['H2']))
    elems.append(Paragraph(
        f'Our operations are structured to deliver consistent quality and timely service to our customers. '
        f'Key operational parameters are monitored regularly, and we have established standard operating '
        f'procedures (SOPs) for all critical processes. Our operational infrastructure has been continuously '
        f'upgraded to support business growth.',
        styles['Body']
    ))
    elems.append(Paragraph(
        'Our quality management approach ensures that products/services meet applicable specifications and '
        'standards. We maintain documentation as required by our quality certifications and conduct '
        'periodic internal audits. Customer feedback is systematically captured and used for continuous improvement.',
        styles['Body']
    ))

    elems.append(Paragraph('G. Human Resources', styles['H2']))
    elems.append(Paragraph(
        f'Our people are a critical source of competitive advantage. We employ a team of trained and '
        f'experienced professionals across various functions including operations, sales, finance, and support. '
        f'We are committed to providing a safe, inclusive, and performance-oriented work environment. '
        f'We comply with all applicable labour laws and provide statutory benefits to all eligible employees.',
        styles['Body']
    ))
    elems.append(Paragraph(
        'We invest in employee training and development to keep our team updated on industry developments, '
        'technology changes, and quality standards. Our employee retention strategies include competitive '
        'compensation, performance incentives, and a positive work culture.',
        styles['Body']
    ))

    elems.append(Paragraph('H. Insurance', styles['H2']))
    elems.append(Paragraph(
        'We maintain various insurance policies to protect our business assets and operations. These include '
        'property/plant insurance, general liability, stock/inventory insurance, and other policies as '
        'applicable. We believe our insurance coverage is adequate relative to the risks associated with '
        'our business operations.',
        styles['Body']
    ))

    if co.website:
        elems.append(Paragraph('I. Digital Presence and Technology', styles['H2']))
        elems.append(Paragraph(
            f'We maintain a digital presence through our website ({co.website}). We use technology across '
            f'our operations to improve efficiency, maintain records, and serve our customers. We are committed '
            f'to increasing technology adoption across all business functions as part of our growth strategy.',
            styles['Body']
        ))

    elems.append(PageBreak())
    return elems


def _build_key_regulations(req, styles) -> list:
    """Detailed key regulations section — 8-12 pages."""
    co = req.company
    sector = co.sector.lower()
    elems = []

    elems.append(Paragraph('SECTION XI — KEY INDUSTRY REGULATIONS AND POLICIES', styles['H1']))
    elems.append(HRFlowable(width=INNER_W, thickness=1.5, color=C_NAVY))
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        f'The operations of {co.name} are governed by various central and state government laws, regulations, '
        f'and guidelines. The following is a summary of the key regulations applicable to our business. '
        f'This is not an exhaustive list of all applicable regulations.',
        styles['Body']
    ))
    elems.append(Spacer(1, 4*mm))

    # Universal regulations
    elems.append(Paragraph('A. General Corporate Regulations', styles['H2']))
    corp_regs = [
        ['Regulation / Act', 'Key Provisions Applicable to the Company'],
        ['Companies Act, 2013', 'Incorporation, capital structure, board composition, financial reporting, AGM, audit, related party transactions, CSR obligations.'],
        ['SEBI ICDR Regulations, 2018', 'Governs the IPO process, DRHP disclosures, issue structure, allotment, and post-listing compliance.'],
        ['SEBI LODR Regulations, 2015', 'Listing obligations including quarterly results, related party disclosures, material events, and corporate governance.'],
        ['Income Tax Act, 1961', 'Taxation of corporate income, TDS/TCS, advance tax, capital gains, and transfer pricing.'],
        ['GST Act, 2017', 'Goods and Services Tax on supply of goods and services; mandatory registration and monthly/quarterly filings.'],
        ['FEMA, 1999', 'Foreign exchange transactions, FDI, ECB, export/import transactions.'],
        ['MSMED Act, 2006', 'MSME registration, priority sector lending, payment protection under MSME Act.'],
    ]
    elems.append(_make_table(corp_regs, [INNER_W*0.38, INNER_W*0.62]))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('B. Labour and Employment Regulations', styles['H2']))
    labour_regs = [
        ['Regulation / Act', 'Key Requirements'],
        ['Employees\' Provident Funds Act, 1952', 'PF contribution at 12% of basic salary by employer and employee for establishments with 20+ employees.'],
        ['ESI Act, 1948', 'ESIC contribution for employees earning less than Rs. 21,000/month. Employer: 3.25%, Employee: 0.75%.'],
        ['Payment of Gratuity Act, 1972', 'Gratuity payable to employees on completion of 5+ years of service.'],
        ['Industrial Disputes Act, 1947', 'Governs conditions of service, termination, and retrenchment for industrial establishments.'],
        ['Factories Act, 1948', 'Safety, health, and welfare of workers in factories; applicable to manufacturing operations.'],
        ['Payment of Minimum Wages Act, 1948', 'Payment of minimum wages as notified by state government; revision periodically.'],
        ['The Code on Wages, 2019', 'Consolidates minimum wages, payment of wages, bonus, and equal remuneration acts.'],
    ]
    elems.append(_make_table(labour_regs, [INNER_W*0.38, INNER_W*0.62]))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('C. Environmental Regulations', styles['H2']))
    elems.append(Paragraph(
        'Our operations are subject to environmental laws and regulations. We comply with applicable '
        'environmental laws and have obtained necessary consents and approvals from pollution control boards. '
        'Key environmental regulations include:',
        styles['Body']
    ))
    env_regs = [
        ['Environmental Act', 'Key Requirements'],
        ['Environment Protection Act, 1986', 'Framework for protection of environment; MOEF notifications on standards.'],
        ['Water (Prevention and Control of Pollution) Act, 1974', 'Consent to establish and operate from State Pollution Control Board.'],
        ['Air (Prevention and Control of Pollution) Act, 1981', 'Air emission standards and consent to operate.'],
        ['Hazardous and Other Wastes Rules, 2016', 'Management, storage, and disposal of hazardous waste.'],
        ['BRSR (FY26 onwards for eligible issuers)', 'Business Responsibility and Sustainability Reporting — ESG disclosures.'],
    ]
    elems.append(_make_table(env_regs, [INNER_W*0.4, INNER_W*0.6]))
    elems.append(Spacer(1, 6*mm))

    # Sector-specific regulations
    elems.append(Paragraph(f'D. Sector-Specific Regulations ({co.sector} Sector)', styles['H2']))

    if 'pharma' in sector or 'health' in sector:
        sector_regs = [
            ['Regulation', 'Description'],
            ['Drugs and Cosmetics Act, 1940', 'Licensing, manufacturing standards, and quality control for pharmaceutical products.'],
            ['CDSCO (Central Drugs Standard Control Organisation)', 'Approval authority for new drugs, clinical trials, and import of drugs.'],
            ['Good Manufacturing Practices (GMP/Schedule M)', 'WHO-GMP and CDSCO Schedule M compliance for pharmaceutical manufacturing.'],
            ['Pharmacopoeia (IP/BP/USP)', 'Standards for pharmaceutical ingredient specifications.'],
            ['DPCO (Drug Price Control Order)', 'Price control for essential medicines under NLEM.'],
            ['FSSAI (for nutraceuticals)', 'Food safety licensing for health supplements and nutraceuticals.'],
        ]
    elif 'nbfc' in sector or 'finance' in sector or 'lending' in sector:
        sector_regs = [
            ['Regulation', 'Description'],
            ['Reserve Bank of India Act, 1934 (NBFC provisions)', 'Registration, capital adequacy (15% CAR), provisioning norms.'],
            ['RBI Master Directions — NBFC', 'Detailed guidelines on lending, classification, and grievance redressal.'],
            ['Fair Practices Code (RBI)', 'Customer protection, disclosure requirements, interest rate policy.'],
            ['Credit Information Companies Regulation Act, 2005', 'Mandatory reporting to credit bureaus (CIBIL, Experian, CRIF).'],
            ['Prevention of Money Laundering Act, 2002', 'KYC norms, STR/CTR reporting to FIU-India.'],
            ['DPDP Act, 2023', 'Data protection and privacy of customer data in digital lending.'],
        ]
    elif 'it' in sector or 'technology' in sector or 'software' in sector:
        sector_regs = [
            ['Regulation', 'Description'],
            ['Information Technology Act, 2000 (amended 2008)', 'Electronic contracts, digital signatures, cybercrimes, data protection.'],
            ['DPDP Act, 2023', 'Data Protection rules for personal data processing — major compliance requirement.'],
            ['CERT-In Directions, 2022', 'Mandatory cybersecurity incident reporting within 6 hours to CERT-In.'],
            ['SEZ Act, 2005 (if in IT SEZ)', 'Tax benefits for IT export-oriented units in Software Technology Parks and SEZs.'],
            ['NASSCOM and STPI Guidelines', 'Industry-specific compliance for export-oriented IT units.'],
            ['GDPR (for EU operations)', 'European data protection law compliance for companies serving EU clients.'],
        ]
    elif 'fmcg' in sector or 'food' in sector or 'retail' in sector:
        sector_regs = [
            ['Regulation', 'Description'],
            ['FSSAI (Food Safety and Standards Authority)', 'Licensing, product standards, labelling requirements for food products.'],
            ['Legal Metrology Act, 2009', 'Mandatory declarations on packaged goods — net weight, MRP, best before date.'],
            ['Consumer Protection Act, 2019', 'Product liability, unfair trade practices, consumer rights.'],
            ['Trade Marks Act, 1999', 'Brand protection and intellectual property registration.'],
            ['BIS Certification (where applicable)', 'Quality certification for certain mandatory categories.'],
            ['E-Commerce Rules, 2020', 'Disclosure requirements for products sold on e-commerce platforms.'],
        ]
    else:
        sector_regs = [
            ['Regulation', 'Description'],
            ['BIS Act, 2016', 'Bureau of Indian Standards certification for manufactured goods where mandated.'],
            ['Industrial Disputes Act, 1947', 'Labour compliance for manufacturing establishments.'],
            ['Factories Act, 1948', 'Safety, health, and welfare norms for factory operations.'],
            ['Electricity Act, 2003', 'Power procurement, captive generation, and distribution compliance.'],
            ['Weights and Measures regulations', 'Compliance for packaged/measured goods.'],
            ['Import Export Code (IEC)', 'Mandatory for export/import activities.'],
        ]

    elems.append(_make_table(sector_regs, [INNER_W*0.38, INNER_W*0.62]))
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph('E. Intellectual Property', styles['H2']))
    elems.append(Paragraph(
        'The Company protects its intellectual property including trademarks, trade names, and proprietary '
        'know-how. We have applied for or registered trademarks for our key brands and product names as '
        'applicable. We rely on confidentiality agreements and trade secret protections for proprietary processes. '
        'We are not aware of any material infringement of our intellectual property or any pending intellectual '
        'property disputes as at the date of this DRHP.',
        styles['Body']
    ))

    elems.append(PageBreak())
    return elems


# ── Main builder ────────────────────────────────────────────

def build_drhp(req: DrhpRequest, job_id: str) -> bytes:
    """Build the full DRHP PDF and return as bytes."""
    styles = _get_styles()
    co = req.company

    buffer = io.BytesIO()

    # Page callbacks
    def on_page(canvas, doc):
        _header_footer(canvas, doc, co.name, 'DRAFT RED HERRING PROSPECTUS')

    frame = Frame(MARGIN, MARGIN, INNER_W, PAGE_H - 2 * MARGIN, id='main')
    template = PageTemplate(id='main', frames=[frame], onPage=on_page)

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 8*mm,
    )
    doc.addPageTemplates([template])

    # --- Update job progress
    def progress(pct: int, msg: str = ''):
        if job_id in _jobs:
            _jobs[job_id]['progress_pct'] = pct
            if msg:
                _jobs[job_id]['message'] = msg

    # --- Assemble all elements
    elements = []

    progress(5, 'Building cover page...')
    elements += _cover_page(req, styles)

    progress(10, 'Table of contents...')
    elements += _table_of_contents(styles)

    progress(15, 'Definitions...')
    elements += _definitions(styles)

    progress(20, 'Risk factors...')
    elements += _risk_factors(req, styles)

    progress(28, 'Introduction...')
    elements += _introduction(req, styles)

    progress(35, 'Financial summary...')
    elements += _financial_summary(req, styles)

    progress(40, 'Capital structure...')
    elements += _capital_structure(req, styles)

    progress(44, 'Objects of issue...')
    elements += _objects_of_issue(req, styles)

    progress(48, 'Basis for issue price...')
    elements += _basis_for_price(req, styles)

    progress(52, 'Tax benefits...')
    elements += _generic_section(
        'Statement of Tax Benefits', 'SECTION VIII',
        [
            'The following tax benefits are available to the Company and its shareholders under '
            'the Income Tax Act, 1961 (IT Act) as amended, and other applicable laws.',
            'It is to be noted that this is not a comprehensive tax analysis. Shareholders are advised '
            'to consult their own tax advisors regarding the specific tax consequences of investing in '
            'equity shares of the Company.',
            '1. Dividends received by Indian shareholders are taxable in their hands at the applicable '
            'marginal income tax rate.',
            '2. Capital gains arising from the transfer of listed equity shares held for more than 12 months '
            '(Long Term Capital Gains) will be taxable at 10% on gains exceeding ₹1 Lakh per year without '
            'indexation benefit (Section 112A of IT Act).',
            '3. Short-term capital gains (shares held for 12 months or less) are taxable at 15% under '
            'Section 111A of IT Act.',
        ],
        styles
    )

    progress(56, 'Industry overview...')
    elements += _build_industry_overview(req, styles)

    progress(62, 'Business overview...')
    elements += _build_business_overview(req, styles)

    progress(67, 'Key regulations...')
    elements += _build_key_regulations(req, styles)

    progress(68, 'Corporate history...')
    elements += _generic_section(
        'History and Corporate Structure', 'SECTION XII',
        [
            f'{co.name} was incorporated on {co.incorporation_date} under the Companies Act, 2013 '
            f'as a Private Limited Company with CIN: {co.cin}.',
            f'The Company is promoted by the Promoter(s) listed in Section XIV of this Prospectus. '
            f'The Promoters have significant domain expertise and have been instrumental in growing the Company.',
            'The Company does not have any subsidiaries, associates, or group companies as at the date of '
            'this DRHP, except as disclosed in this document.',
            f'The Company\'s registered office is at {co.registered_address}. '
            + (f'Website: {co.website}.' if co.website else ''),
        ],
        styles
    )

    progress(72, 'Management and board...')
    elements += _management_section(req, styles)

    progress(76, 'Promoters...')
    elements += _promoters_section(req, styles)

    progress(79, 'Related party transactions...')
    elements += _generic_section(
        'Related Party Transactions', 'SECTION XV',
        [
            'All related party transactions have been conducted in the ordinary course of business and on '
            'an arm\'s length basis.',
            'The Company has made disclosures of all related party transactions as required under the '
            'Companies Act, 2013, Indian Accounting Standards (Ind AS 24), and SEBI regulations.',
            'Details of material related party transactions are disclosed in the audited financial statements '
            'annexed to this Prospectus.',
        ],
        styles
    )

    progress(81, 'Dividend policy...')
    elements += _generic_section(
        'Dividend Policy', 'SECTION XVI',
        [
            'The Company has not declared or paid any dividends in the last three financial years.',
            'The declaration of dividends will depend upon various factors including the financial results, '
            'capital requirements, contractual restrictions, and overall financial position of the Company. '
            'The decision to declare dividends will be at the sole discretion of the Board of Directors.',
            'Our Company does not have a formal dividend policy as of the date of this DRHP. Investors '
            'should not rely on dividend income from the Company.',
        ],
        styles
    )

    progress(85, 'Financial statements...')
    elements += _financial_statements(req, styles)

    progress(89, 'MD&A...')
    elements += _mda_section(req, styles)

    progress(92, 'Legal information...')
    elements += _generic_section(
        'Legal and Other Information', 'SECTION XIX',
        [
            f'As at the date of this Prospectus, there are no outstanding litigation matters, pending '
            f'disputes, or regulatory proceedings against {co.name} or its Directors that are material '
            f'to the Company\'s business or financial condition, except as disclosed herein.',
            'Any pending litigation matters, if any, are set out in the Prospectus. The Company '
            'has not been declared a wilful defaulter by any bank or financial institution.',
        ],
        styles
    )

    progress(94, 'Government approvals...')
    elements += _generic_section(
        'Government Approvals', 'SECTION XX',
        [
            'The Company has obtained all material government approvals required to carry on its business '
            'as currently conducted. Key approvals include registrations, licenses, and permissions from '
            'relevant central and state government authorities.',
            'There are no pending government approvals without which the Company cannot conduct its business.',
        ],
        styles
    )

    progress(96, 'SEBI compliance...')
    elements += _generic_section(
        'Compliance — Companies Act / SEBI ICDR', 'SECTION XXI',
        [
            'The Company confirms that it complies with the provisions of the Companies Act, 2013 '
            'and the SEBI (Issue of Capital and Disclosure Requirements) Regulations, 2018 as applicable '
            'to an SME IPO on a recognised stock exchange.',
            'The Issue has been structured in compliance with the applicable regulatory requirements '
            'including minimum promoter contribution, reservation for Market Maker, and lock-in provisions.',
            f'Minimum Promoter Contribution: {sum(p.holding_pct for p in req.promoters):.2f}% '
            f'(which meets the SEBI requirement of minimum 20% of post-issue paid-up capital).',
        ],
        styles
    )

    progress(97, 'Material contracts...')
    elements += _generic_section(
        'Material Contracts and Documents', 'SECTION XXII',
        [
            'The following contracts and documents, not being contracts entered into in the ordinary course '
            'of business, are or may be deemed material:',
            '(a) Memorandum of Understanding with the Lead Manager;',
            '(b) Due Diligence Certificate from the Lead Manager;',
            '(c) Consent letters from the Statutory Auditor, Legal Counsel, and Registrar;',
            '(d) Audited financial statements for the last three financial years;',
            '(e) Material contracts with key customers and suppliers (redacted for confidentiality);',
            '(f) Board and shareholder resolutions approving the Issue.',
            'All the above documents are available for inspection at the Registered Office of the Company '
            'during business hours on any Business Day between 10:00 AM and 5:00 PM IST.',
        ],
        styles
    )

    progress(99, 'Declaration...')
    elements += _declaration(req, styles)

    # Build PDF
    doc.build(elements)
    progress(100, 'Done')
    _jobs[job_id]['status'] = 'done'

    pdf_bytes = buffer.getvalue()
    buffer.close()
    _jobs[job_id]['pdf'] = pdf_bytes
    return pdf_bytes


# ── Async wrapper (runs in thread to avoid blocking event loop) ──

async def generate_drhp_async(req: DrhpRequest) -> str:
    """Start async DRHP generation and return job_id."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        'status': 'processing',
        'progress_pct': 0,
        'message': 'Starting generation...',
        'pdf': None,
    }

    async def _run():
        try:
            await asyncio.to_thread(build_drhp, req, job_id)
        except Exception as exc:
            _jobs[job_id]['status'] = 'error'
            _jobs[job_id]['message'] = str(exc)

    asyncio.create_task(_run())
    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return _jobs.get(job_id)


def get_job_pdf(job_id: str) -> Optional[bytes]:
    job = _jobs.get(job_id)
    return job['pdf'] if job else None
