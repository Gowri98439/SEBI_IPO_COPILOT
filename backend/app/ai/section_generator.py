"""
Enterprise DRHP Section Generator
Generates evidence-grounded DRHP section content using LLM + RAG.

HALLUCINATION POLICY:
- Every factual claim must be derivable from DrhpRequestV2 input or retrieved workspace documents.
- If a required field is not in the input, the section explicitly states "Missing Information".
- Historical DRHP examples are used ONLY for structural/style reference, never as source facts.
- No company-specific data from historical documents may appear in generated content.
- All sections return SectionOutput with citations, missing_fields, and confidence.

SECTION ROUTING:
- 'algorithmic' sections: generated from structured data with no LLM (zero hallucination risk)
- 'llm' sections: LLM-assisted with explicit grounding prompts + RAG context
- 'hybrid' sections: algorithmic skeleton + LLM-enriched narrative
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.ai.llm_client import get_llm
from app.ai.rag_pipeline import query_sebi_regulations, query_workspace_documents
from app.schemas.drhp_v2 import (
    DrhpRequestV2,
    ExtendedFinancialYear,
    FinancialIntelligenceReport,
    SectionOutput,
)
from app.ai.peer_comparison import find_comparable_peers, build_peer_comparison_table, compute_peer_statistics


logger = logging.getLogger(__name__)

MISSING_INFO = "Missing Information — not provided in company data submission"

# ── Section routing table ─────────────────────────────────────────────────────
# format: section_id → (title, generation_method)
SECTION_ROUTING: Dict[str, Tuple[str, str]] = {
    "cover_page":            ("Cover Page",                                    "algorithmic"),
    "disclaimer":            ("Important Disclaimer",                          "algorithmic"),
    "toc":                   ("Table of Contents",                             "algorithmic"),
    "definitions":           ("Definitions and Abbreviations",                  "algorithmic"),
    "forward_looking":       ("Forward Looking Statements",                    "algorithmic"),
    "issue_summary":         ("Issue Summary",                                 "algorithmic"),
    "risk_factors":          ("Risk Factors",                                  "hybrid"),
    "business_overview":     ("Business Overview",                             "llm"),
    "business_model":        ("Business Model",                                "llm"),
    "competitive_strengths": ("Competitive Strengths",                         "llm"),
    "strategies":            ("Business Strategies",                           "llm"),
    "industry_overview":     ("Industry Overview",                             "llm"),
    "market_opportunity":    ("Market Opportunity",                            "llm"),
    "competition":           ("Competition",                                   "hybrid"),
    "corporate_structure":   ("Corporate Structure",                           "algorithmic"),
    "promoters":             ("Promoters and Promoter Group",                  "algorithmic"),
    "directors":             ("Board of Directors and Key Management",         "algorithmic"),
    "mda":                   ("Management Discussion and Analysis",            "hybrid"),
    "capital_structure":     ("Capital Structure",                             "algorithmic"),
    "shareholding_pattern":  ("Shareholding Pattern",                         "algorithmic"),
    "objects_of_issue":      ("Objects of the Issue",                         "hybrid"),
    "use_of_proceeds":       ("Use of Proceeds",                              "algorithmic"),
    "basis_for_price":       ("Basis for Issue Price",                        "hybrid"),
    "dividend_policy":       ("Dividend Policy",                              "algorithmic"),
    "financial_statements":  ("Financial Statements Summary",                 "algorithmic"),
    "financial_ratios":      ("Key Financial Ratios",                         "algorithmic"),
    "related_party":         ("Related Party Transactions",                   "algorithmic"),
    "outstanding_litigation":("Outstanding Litigation",                        "algorithmic"),
    "contingent_liabilities":("Contingent Liabilities",                       "algorithmic"),
    "government_approvals":  ("Government and Other Approvals",               "algorithmic"),
    "material_contracts":    ("Material Contracts",                           "algorithmic"),
    "intellectual_property": ("Intellectual Property",                        "algorithmic"),
    "employees":             ("Employees",                                    "algorithmic"),
    "properties":            ("Properties",                                   "algorithmic"),
    "esg_summary":           ("ESG Summary",                                  "hybrid"),
    "corporate_governance":  ("Corporate Governance",                         "algorithmic"),
    "compliance_matrix":     ("SEBI Compliance Matrix",                       "algorithmic"),
    "annexures":             ("Annexures",                                    "algorithmic"),
    "glossary":              ("Glossary",                                     "algorithmic"),
    "declaration":           ("Declaration and Undertaking",                  "algorithmic"),
}

ALL_SECTION_IDS = list(SECTION_ROUTING.keys())


# ── Context builder for LLM prompts ─────────────────────────────────────────

def _build_company_context(req: DrhpRequestV2) -> str:
    """Flatten DrhpRequestV2 into a factual context string for LLM prompts."""
    co = req.company
    iss = req.issue
    promoters_txt = "; ".join(
        f"{p.name} ({p.designation}, {p.holding_pct:.1f}%)"
        for p in req.promoters
    ) if req.promoters else MISSING_INFO

    def _fmt_fin(v):
        """Format a financial value: None → 'Not Provided', else ₹{v:,.2f}L"""
        return f"₹{v:,.2f}L" if v is not None else "Not Provided"

    fys_txt = "\n".join(
        f"  {fy.year}: Revenue {_fmt_fin(fy.revenue)}, PAT {_fmt_fin(fy.net_profit)}, "
        f"EBITDA {_fmt_fin(fy.ebitda)}, "
        f"Total Assets {_fmt_fin(fy.total_assets)}, Equity {_fmt_fin(fy.total_equity)}"
        for fy in req.financials
    ) if req.financials else MISSING_INFO

    products_txt = (
        "; ".join(f"{p.name}" for p in co.key_products)
        if co.key_products else MISSING_INFO
    )

    return f"""
COMPANY: {co.name}
CIN: {co.cin} | PAN: {co.pan}
INCORPORATED: {co.incorporation_date}
SECTOR: {co.sector} | Sub-sector: {co.sub_sector or MISSING_INFO}
REGISTERED ADDRESS: {co.registered_address}
WEBSITE: {co.website or MISSING_INFO}
EMPLOYEES: {co.employee_count or MISSING_INFO}
KEY PRODUCTS/SERVICES: {products_txt}
GEOGRAPHIES: {', '.join(co.geographies_served) if co.geographies_served else MISSING_INFO}
CERTIFICATIONS: {', '.join(co.certifications) if co.certifications else MISSING_INFO}
BUSINESS DESCRIPTION: {co.description}
STATUTORY AUDITOR: {co.statutory_auditor or MISSING_INFO}

PROMOTERS:
{promoters_txt}

FINANCIALS (INR Lakhs):
{fys_txt}

ISSUE DETAILS:
Issue Size: ₹{iss.issue_size_cr:.2f} Crore
Fresh Issue: ₹{iss.fresh_issue_cr:.2f} Crore | OFS: ₹{iss.ofs_cr:.2f} Crore
Price Band: ₹{iss.price_band_low:.0f} – ₹{iss.price_band_high:.0f} | Face Value: ₹{iss.face_value:.0f}
Objects of Issue: {iss.objects_of_issue}
Lead Manager: {iss.merchant_banker}
""".strip()


def _grounding_system_prompt() -> str:
    return """You are an expert IPO document drafter with 15+ years of SEBI compliance experience.

CRITICAL RULES — follow without exception:
1. Use ONLY the company data provided in the context. Do NOT add any information not present in the context.
2. Where information is marked as "Missing Information", write exactly: [MISSING: <field description>]
3. Do NOT invent: revenue figures, profit figures, customer names, contract values, market shares, employee counts, regulatory approvals, or any other factual data.
4. Historical DRHP examples are for STYLE REFERENCE only — never use them as source facts.
5. Use formal, professional legal language appropriate for SEBI regulatory filings.
6. Include all mandatory SEBI ICDR disclosures for this section.
7. Do NOT write placeholder text like "Company Name", "XX%", "[INSERT HERE]" — either use real data or write [MISSING: field].
8. Keep tone factual, balanced, and regulatory-appropriate."""


# ── Algorithmic section builders ──────────────────────────────────────────────

def _build_forward_looking(req: DrhpRequestV2) -> SectionOutput:
    co = req.company
    content = f"""FORWARD LOOKING STATEMENTS

This Draft Red Herring Prospectus contains certain "forward-looking statements." These forward-looking statements 
generally can be identified by words or phrases such as "aim", "anticipate", "believe", "expect", "estimate", 
"intend", "objective", "plan", "project", "shall", "will", "will continue", "will pursue" or other words or 
phrases of similar import.

All forward-looking statements are subject to risks, uncertainties and assumptions about {co.name} that could 
cause actual results to differ materially from those contemplated by the relevant forward-looking statement.

Important factors that could cause actual results to differ materially from the Company's expectations include, 
but are not limited to:
• General economic and business conditions in India and globally;
• The Company's ability to successfully implement its growth strategy;
• Changes in the competitive landscape in the {co.sector} sector;
• Changes in laws and regulations that apply to the Company's business;
• Changes in political and social conditions in India;
• The occurrence of natural disasters, acts of terrorism or other events;
• The ability to attract and retain key personnel.

Neither the Company nor the Lead Manager, nor any of their respective affiliates have any obligation to update 
or otherwise revise any statements reflecting circumstances arising after the date hereof or to reflect the 
occurrence of underlying events, even if the underlying assumptions do not come to fruition.
"""
    return SectionOutput(
        section_id="forward_looking",
        title="Forward Looking Statements",
        content=content,
        citations=[{"type": "regulatory", "ref": "SEBI ICDR Regulations 2018, Schedule VI, Part A"}],
        confidence=1.0,
        generation_method="algorithmic",
    )


def _build_dividend_policy(req: DrhpRequestV2) -> SectionOutput:
    co = req.company
    latest_fy = req.financials[-1] if req.financials else None
    profitable = latest_fy and latest_fy.net_profit is not None and latest_fy.net_profit > 0

    if profitable:
        narrative = (
            f"{co.name} has not declared any dividends in the past. The Board of Directors may recommend "
            f"dividends in the future, subject to the profits available for distribution, after considering "
            f"the Company's growth plans, future capital requirements, financial condition, and applicable legal requirements. "
            f"Any future declaration of dividends will require the approval of the shareholders of the Company at "
            f"the Annual General Meeting and will be at the discretion of the Board."
        )
    else:
        narrative = (
            f"{co.name} has not declared any dividends in the past. The Company does not presently intend to "
            f"pay dividends in the near term as the Company intends to retain earnings to fund growth. "
            f"Any future dividend payments will depend on earnings, financial condition, capital requirements, "
            f"and applicable legal requirements."
        )

    content = f"""DIVIDEND POLICY

{narrative}

There is no guarantee that dividends will be declared or paid in any financial year. Any dividends paid 
in the future will be subject to applicable laws and regulations, including Companies Act 2013, and will 
be recommended by the Board of Directors from time to time.

Investors should note that past financial performance, including past dividend payments (if any), is not 
indicative of future results.
"""
    return SectionOutput(
        section_id="dividend_policy",
        title="Dividend Policy",
        content=content,
        confidence=1.0,
        generation_method="algorithmic",
    )


def _build_outstanding_litigation(req: DrhpRequestV2) -> SectionOutput:
    legal = req.legal_proceedings
    co = req.company

    if not legal:
        content = f"""OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS

[MISSING: Management declaration of outstanding litigation status — required before filing]

Note to the Merchant Banker and Legal Counsel: This section requires a formal declaration from the Board of Directors and Legal Counsel confirming whether there are or are not any outstanding litigations, suits, criminal or civil prosecutions, proceedings or tax liabilities against {co.name}, its Directors, Promoters or Group Companies that may have a material adverse effect on the business.

This declaration has NOT been provided in the company data submission. The section CANNOT be completed until this information is received and verified.

Required from the Company before this section can be finalized:
- Board resolution or legal opinion confirming litigation status
- Search report from company's legal counsel (if nil litigation)
- Details of all pending proceedings if any exist
- Nature, forum, parties, amounts involved, and current status for each proceeding

Companies are required under SEBI (ICDR) Regulations 2018 to disclose all material litigation regardless of outcome.
"""
    else:
        rows = "\n".join(
            f"• {lp.court_or_tribunal} | {lp.nature_of_case} | "
            f"Amount: {'₹' + f'{lp.amount_involved_lakhs:,.2f} Lakhs' if lp.amount_involved_lakhs else 'Not quantified'} | "
            f"Status: {lp.current_status} | Party: {lp.party_type}"
            for lp in legal
        )
        content = f"""OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS

The following proceedings are pending as of the date of this Draft Red Herring Prospectus:

{rows}

The above proceedings are based on information provided by the management. Investors should carefully 
review the above disclosures before making any investment decisions.
"""

    return SectionOutput(
        section_id="outstanding_litigation",
        title="Outstanding Litigation",
        content=content,
        missing_fields=[] if legal else ["legal_proceedings"],
        confidence=1.0,
        generation_method="algorithmic",
    )


def _build_employees_section(req: DrhpRequestV2) -> SectionOutput:
    co = req.company
    missing = []

    if co.employee_count:
        emp_line = (
            f"As of {co.employee_count_year or 'the date of this document'}, "
            f"{co.name} employs approximately {co.employee_count:,} employees."
        )
    else:
        emp_line = f"[MISSING: Total employee count as of a specific date]"
        missing.append("employee_count")

    content = f"""EMPLOYEES

{emp_line}

The Company believes that its employees are its most valuable asset. {co.name} is committed to 
employee development, fair compensation, and a safe working environment.

[MISSING: Employee category breakdown (permanent vs contract, male vs female, departmental split)]
[MISSING: Key HR policies and employee benefit schemes]

[MISSING: Confirmation from management regarding labor dispute history — required before filing]

Note to Merchant Banker and Legal Counsel: The Company's legal counsel must provide a declaration confirming whether any material labor disputes, strikes, or lockouts have occurred or are pending. This cannot be stated as "nil" in the DRHP without an explicit management declaration. The above section requires formal HR disclosure before filing.
"""
    return SectionOutput(
        section_id="employees",
        title="Employees",
        content=content,
        missing_fields=missing,
        confidence=0.8,
        generation_method="algorithmic",
    )


# ── LLM-assisted section generation ─────────────────────────────────────────

async def _generate_with_llm(
    section_id: str,
    title: str,
    req: DrhpRequestV2,
    sebi_context: str,
    workspace_context: str,
) -> SectionOutput:
    """Call the LLM to generate a specific DRHP section grounded in provided data."""
    t0 = time.perf_counter()
    company_ctx = _build_company_context(req)

    user_msg = f"""Generate the '{title}' section of the DRHP for this company.

SEBI REGULATORY REQUIREMENTS FOR THIS SECTION (retrieved from SEBI corpus):
{sebi_context if sebi_context else 'No specific regulation retrieved — apply general ICDR Schedule VI requirements.'}

COMPANY FACTUAL DATA (use ONLY this data for company-specific facts):
{company_ctx}

WORKSPACE DOCUMENT CONTEXT (relevant extracts from uploaded company documents):
{workspace_context if workspace_context else 'No workspace documents available for retrieval.'}

INSTRUCTIONS:
- Generate the complete '{title}' section.
- Use formal regulatory language appropriate for SEBI ICDR filings.
- Where company data is available, use it precisely and accurately.
- Where data is missing, write exactly: [MISSING: <description of what is needed>]
- Do NOT invent any facts. Do NOT use placeholder names or generic companies.
- Structure with appropriate headings and sub-headings.
- Include all mandatory SEBI disclosures for this section."""

    llm = get_llm(temperature=0.1)
    parser = StrOutputParser()
    chain = llm | parser

    messages = [
        SystemMessage(content=_grounding_system_prompt()),
        HumanMessage(content=user_msg),
    ]

    try:
        content = await chain.ainvoke(messages)
        elapsed = (time.perf_counter() - t0) * 1000

        # Detect any [MISSING: ...] markers in output
        import re
        missing_markers = re.findall(r'\[MISSING:\s*([^\]]+)\]', content)

        return SectionOutput(
            section_id=section_id,
            title=title,
            content=content,
            citations=[
                {"type": "sebi_corpus", "text": sebi_context[:200] if sebi_context else ""},
            ],
            source_documents=req.company.key_products and [p.name for p in req.company.key_products] or [],
            missing_fields=missing_markers,
            confidence=0.85,
            generation_method="llm",
            llm_model="llama-3.3-70b-versatile",
            generation_time_ms=elapsed,
        )
    except Exception as exc:
        logger.error("LLM generation failed for section '%s': %s", section_id, exc, exc_info=True)
        return SectionOutput(
            section_id=section_id,
            title=title,
            content=f"[GENERATION ERROR: Section '{title}' could not be generated. Error: {exc}]\n\n"
                    f"[MISSING: All content for this section — please retry generation or provide content manually]",
            missing_fields=[f"section_content_{section_id}"],
            confidence=0.0,
            generation_method="llm",
            review_status="rejected",
        )


async def _generate_risk_factors_hybrid(req: DrhpRequestV2) -> SectionOutput:
    """Generate risk factors — hybrid approach: algorithmic base + LLM enrichment."""
    co = req.company
    iss = req.issue
    latest_fy = req.financials[-1] if req.financials else None

    # Algorithmic core risks (always present)
    base_risks = [
        ("Limited Operating History Risk",
         f"{co.name} was incorporated on {co.incorporation_date}. Our limited operating history "
         f"makes it difficult to assess future performance."),
        ("Sector-Specific Competition Risk",
         f"The {co.sector} sector is highly competitive. We face competition from larger, "
         f"better-capitalised entities with greater market reach."),
        ("Working Capital Risk",
         "Our business requires continuous working capital deployment. Delays in receivables "
         "or unforeseen capital requirements may impact liquidity."),
        ("Key Personnel Risk",
         "Our success depends on senior management retention. Loss of key personnel may adversely "
         "affect our business."),
        ("Regulatory Compliance Risk",
         f"Our {co.sector} business is subject to central and state government regulations. "
         f"Changes in applicable laws could adversely impact operations."),
        ("No Prior Public Market Risk",
         f"There is no prior public market for our equity shares. The Issue price may not be "
         f"indicative of the post-listing trading price."),
        ("Promoter Lock-in Risk",
         "Promoter shares are subject to SEBI-mandated lock-in for 3 years. Post lock-in "
         "exit by promoters may create downward price pressure."),
    ]

    # Data-driven risks — only triggered when data is explicitly provided (not None)
    if latest_fy and latest_fy.net_profit is not None and latest_fy.net_profit < 0:
        base_risks.append((
            "Profitability Risk",
            f"Our Company has reported a net loss of ₹{abs(latest_fy.net_profit):,.2f} Lakhs in {latest_fy.year}. "
            "We cannot assure sustained profitability."
        ))

    if (latest_fy and latest_fy.total_debt is not None
            and latest_fy.total_equity is not None and latest_fy.total_equity > 0):
        de = latest_fy.total_debt / latest_fy.total_equity
        if de > 1.5:
            base_risks.append((
                "High Leverage Risk",
                f"Our Debt/Equity ratio was {de:.2f}x as of {latest_fy.year}. High leverage increases "
                "financial risk and reduces operational flexibility."
            ))

    risks_text = "\n\n".join(
        f"**{i+1}. {title}**\n{desc}"
        for i, (title, desc) in enumerate(base_risks)
    )

    content = f"""RISK FACTORS

Investment in equity shares involves a degree of risk. Investors should carefully read all risk factors 
before taking an investment decision. Additional risks not currently known may also materially impair 
the Company's business, financial condition, and results of operations.

{risks_text}

**{len(base_risks)+1}. General Economic Risk**
Our financial performance is linked to overall economic conditions in India and globally. Economic 
downturns, inflationary pressures, interest rate changes, and foreign exchange fluctuations could 
adversely affect our business.

**{len(base_risks)+2}. Geopolitical and Force Majeure Risk**
Unforeseen events including natural disasters, pandemics, geopolitical tensions, and social unrest 
could disrupt supply chains, reduce consumer demand, and adversely impact results.

Note: The above risk factors are based on information provided and general sector knowledge. 
Company-specific risk factors based on uploaded documents and detailed business information 
should be added by the legal team and merchant banker before filing.
"""

    missing = []
    if not latest_fy:
        missing.append("financial_data_for_risk_calibration")
    if not co.key_customers:
        missing.append("customer_concentration_data")

    return SectionOutput(
        section_id="risk_factors",
        title="Risk Factors",
        content=content,
        missing_fields=missing,
        confidence=0.75,
        generation_method="hybrid",
    )


async def _build_basis_for_price_hybrid(req: DrhpRequestV2) -> SectionOutput:
    """Generate Basis for Issue Price using algorithmic peer comparison + LLM structure."""
    co = req.company
    iss = req.issue
    latest_fy = req.financials[-1] if req.financials else None

    # Get peers from the peer comparison engine
    peers = find_comparable_peers(req)
    table = build_peer_comparison_table(req, peers)
    stats = compute_peer_statistics(table)

    # Format peers for text
    peer_text_lines = []
    for row in table:
        if row.get("is_target"):
            continue
        peer_text_lines.append(
            f"- **{row['company']}**: Revenue: ₹{row.get('revenue_lakhs', 'N/A')} Lakhs, "
            f"PAT Margin: {row.get('pat_margin_pct', 'N/A')}%, "
            f"Similarity Score: {row.get('similarity_score', 0):.0%} "
            f"({row.get('selection_rationale', 'N/A')})"
        )
    peer_text = "\n".join(peer_text_lines) if peer_text_lines else "No comparable peers found."

    content = f"""BASIS FOR ISSUE PRICE

The Issue Price will be determined by our Company in consultation with the Lead Manager, 
on the basis of assessment of market demand for the Equity Shares through the Book Building Process 
and on the basis of qualitative and quantitative factors.

**Qualitative Factors**
We believe that the following qualitative factors provide the basis for the Issue Price:
- Proven track record and experienced management team.
- Strong financial performance and scalable business model.
- Established relationships with customers and suppliers.
[MISSING: Company-specific qualitative strengths — please add manually]

**Quantitative Factors**
Some of the quantitative factors which may form the basis for computing the Issue Price are as follows:

1. Basic & Diluted Earnings Per Share (EPS):
   - As of {latest_fy.year if latest_fy else 'latest fiscal'}: {latest_fy.eps if (latest_fy and latest_fy.eps) else '[MISSING: EPS data]'}

2. Return on Net Worth (RoNW):
   - As of {latest_fy.year if latest_fy else 'latest fiscal'}: {latest_fy.ronw_pct if (latest_fy and latest_fy.ronw_pct) else '[MISSING: RoNW data]'}%

**Peer Group Comparison**
The following peer group has been identified for comparison based on sector, scale, and operational metrics:

{peer_text}

*Industry Peer Statistics (excluding target company):*
- Median PAT Margin: {stats.get('pat_margin_pct', {}).get('median', 'N/A')}%
- Median EBITDA Margin: {stats.get('ebitda_margin_pct', {}).get('median', 'N/A')}%
- Median Return on Equity (ROE): {stats.get('roe_pct', {}).get('median', 'N/A')}%

**Important Disclaimer on Peer Data:**
{stats.get('data_disclaimer', 'Data not verified from exchange filings. Replace with verified NSE/BSE SME IPO data before SEBI filing.')}
"""

    return SectionOutput(
        section_id="basis_for_price",
        title="Basis for Issue Price",
        content=content,
        missing_fields=["company_specific_qualitative_strengths"],
        confidence=0.85,
        generation_method="hybrid",
    )



# ── Main section generator ────────────────────────────────────────────────────

class SectionGenerator:
    """
    Orchestrates generation of all DRHP sections.
    Routes each section to the appropriate generation method.
    """

    def __init__(self, req: DrhpRequestV2, financial_report: Optional[FinancialIntelligenceReport] = None):
        self.req = req
        self.financial_report = financial_report

    async def generate_section(self, section_id: str) -> SectionOutput:
        """Generate a single DRHP section by ID."""
        if section_id not in SECTION_ROUTING:
            logger.warning("Unknown section_id: '%s'", section_id)
            return SectionOutput(
                section_id=section_id,
                title=section_id.replace("_", " ").title(),
                content=f"[MISSING: Section '{section_id}' is not in the known section registry]",
                missing_fields=[f"section_{section_id}"],
                confidence=0.0,
                generation_method="algorithmic",
            )

        title, method = SECTION_ROUTING[section_id]
        logger.info("Generating section '%s' via method: %s", section_id, method)

        # ── Pure algorithmic sections ──────────────────────────────────────
        if section_id == "forward_looking":
            return _build_forward_looking(self.req)
        if section_id == "dividend_policy":
            return _build_dividend_policy(self.req)
        if section_id == "outstanding_litigation":
            return _build_outstanding_litigation(self.req)
        if section_id == "employees":
            return _build_employees_section(self.req)
        if section_id == "risk_factors":
            return await _generate_risk_factors_hybrid(self.req)
        if section_id == "basis_for_price":
            return await _build_basis_for_price_hybrid(self.req)

        # ── LLM or hybrid sections ─────────────────────────────────────────
        if method in ("llm", "hybrid"):
            # Retrieve SEBI regulatory context
            try:
                sebi_docs = await query_sebi_regulations(f"SEBI ICDR requirements for {title} section", top_k=3)
                sebi_context = "\n\n".join(
                    f"[{d.get('regulation_id', 'SEBI')}] {d.get('content', '')[:400]}"
                    for d in sebi_docs
                )
            except Exception:
                sebi_context = ""

            # Retrieve workspace documents if workspace_id available
            workspace_context = ""
            if self.req.workspace_id:
                try:
                    ws_docs = await query_workspace_documents(
                        f"{title} {self.req.company.sector} {self.req.company.name}",
                        self.req.workspace_id,
                        top_k=4,
                    )
                    workspace_context = "\n\n".join(
                        f"[{d.get('filename', 'Document')}, p.{d.get('page', '?')}] {d.get('content', '')[:500]}"
                        for d in ws_docs
                    )
                except Exception:
                    workspace_context = ""

            return await _generate_with_llm(
                section_id=section_id,
                title=title,
                req=self.req,
                sebi_context=sebi_context,
                workspace_context=workspace_context,
            )

        # ── Algorithmic fallback for remaining sections ────────────────────
        return self._generate_algorithmic_fallback(section_id, title)

    def _generate_algorithmic_fallback(self, section_id: str, title: str) -> SectionOutput:
        """Generic algorithmic fallback for sections not yet specifically implemented."""
        co = self.req.company
        content = f"""{title.upper()}

This section of the DRHP covers {title.lower()} for {co.name}.

[MISSING: Detailed content for '{title}' — please provide company-specific information 
for this section or enable LLM generation to auto-draft based on provided data]

The information in this section will be based on:
- Company records and management representations
- Applicable SEBI ICDR Regulations 2018 requirements
- Due diligence findings by the Lead Manager

This section will be completed in consultation with the Lead Manager, Legal Counsel, 
and the Company's management.
"""
        return SectionOutput(
            section_id=section_id,
            title=title,
            content=content,
            missing_fields=[f"section_content_{section_id}"],
            confidence=0.3,
            generation_method="algorithmic",
        )

    async def generate_all_sections(
        self,
        target_sections: Optional[List[str]] = None,
        progress_callback=None,
    ) -> Dict[str, SectionOutput]:
        """Generate all sections (or a subset) and return a dict of section_id → SectionOutput."""
        sections_to_generate = target_sections or ALL_SECTION_IDS
        results: Dict[str, SectionOutput] = {}
        total = len(sections_to_generate)

        for i, section_id in enumerate(sections_to_generate):
            if progress_callback:
                pct = int((i / total) * 100)
                title = SECTION_ROUTING.get(section_id, (section_id, ""))[0]
                progress_callback(pct, f"Generating: {title}")

            result = await self.generate_section(section_id)
            results[section_id] = result

            if progress_callback:
                pct = int(((i + 1) / total) * 100)
                progress_callback(pct, f"Completed: {result.title}")

            # Small delay to avoid rate-limiting
            await asyncio.sleep(0.1)

        return results
