"""
Enterprise DRHP v2 — Extended Pydantic Schema Models
All new fields are Optional with defaults — fully backward-compatible with drhp.py v1.

This module extends the base DrhpRequest with:
- Richer financial data (required for 25+ ratio computation)
- Legal, ESG, credit, and operational fields
- Provenance tracking for every financial value
- Use-of-proceeds structured breakdown
- Peer company references
- Pipeline control flags
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Provenance tracking ─────────────────────────────────────────────────────

class DataProvenance(BaseModel):
    """Tracks where a data point came from — required for evidence trail."""
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    extraction_method: Optional[str] = None   # "manual_input" | "ocr" | "parsed_excel" | "api"
    confidence: float = 1.0
    financial_year: Optional[str] = None
    unit: str = "INR_Lakhs"
    currency: str = "INR"
    formula: Optional[str] = None             # If derived, e.g. "EBITDA = Revenue - COGS - Opex"
    rounding_policy: Optional[str] = "2dp"
    verified_by: Optional[str] = None


# ── Extended Financial Year ─────────────────────────────────────────────────

class ExtendedFinancialYear(BaseModel):
    """
    Full financial year data required for comprehensive ratio computation.
    All fields Optional — missing fields cause ratios to return 'Missing Information'
    rather than incorrect calculations.
    """
    year: str = Field(..., description="Financial year, e.g. '2023-24'")

    # P&L — core
    # CRITICAL: All financial fields are Optional[float] defaulting to None.
    # MISSING != ZERO. A missing field returns None → "Not Provided" in display.
    # An explicit zero from the user (e.g., revenue: 0) is a valid zero disclosure.
    revenue: Optional[float] = Field(None, description="Total revenue/turnover in INR Lakhs")
    gross_profit: Optional[float] = Field(None, description="Revenue minus COGS")
    ebitda: Optional[float] = Field(None, description="EBITDA in INR Lakhs")
    depreciation: Optional[float] = Field(None, description="D&A in INR Lakhs")
    ebit: Optional[float] = Field(None, description="EBIT (EBITDA - D&A)")
    interest_expense: Optional[float] = Field(None, description="Finance costs in INR Lakhs")
    pbt: Optional[float] = Field(None, description="Profit before tax")
    tax_expense: Optional[float] = Field(None, description="Tax expense in INR Lakhs")
    net_profit: Optional[float] = Field(None, description="PAT in INR Lakhs")
    operating_expenses: Optional[float] = Field(None, description="Total operating expenses ex-D&A")
    cogs: Optional[float] = Field(None, description="Cost of goods sold")

    # Balance Sheet — Assets
    total_assets: Optional[float] = Field(None, description="Total assets in INR Lakhs")
    current_assets: Optional[float] = Field(None, description="Current assets")
    cash_and_equivalents: Optional[float] = Field(None, description="Cash + liquid investments")
    inventory: Optional[float] = Field(None, description="Inventory at period end")
    trade_receivables: Optional[float] = Field(None, description="Accounts receivable")
    fixed_assets: Optional[float] = Field(None, description="Net fixed assets / PP&E")
    intangible_assets: Optional[float] = Field(None, description="Goodwill + intangibles")
    capex: Optional[float] = Field(None, description="Capital expenditure in INR Lakhs")

    # Balance Sheet — Liabilities & Equity
    total_equity: Optional[float] = Field(None, description="Net worth / shareholders equity")
    total_debt: Optional[float] = Field(None, description="Total borrowings (LT + ST)")
    long_term_debt: Optional[float] = Field(None, description="Long-term borrowings")
    short_term_debt: Optional[float] = Field(None, description="Short-term borrowings + current portion")
    current_liabilities: Optional[float] = Field(None, description="Total current liabilities")
    trade_payables: Optional[float] = Field(None, description="Accounts payable")
    total_liabilities: Optional[float] = Field(None, description="Total liabilities")

    # Cash Flow
    operating_cash_flow: Optional[float] = Field(None, description="Cash from operations")
    investing_cash_flow: Optional[float] = Field(None, description="Cash from investing activities")
    financing_cash_flow: Optional[float] = Field(None, description="Cash from financing activities")
    free_cash_flow: Optional[float] = Field(None, description="FCF = OCF - Capex")

    # Share Data
    shares_outstanding: Optional[float] = Field(None, description="Weighted avg shares (in units, not lakhs)")
    face_value_per_share: Optional[float] = Field(None, description="Face value of equity share")

    # Provenance
    provenance: Optional[DataProvenance] = None
    audited: bool = True
    auditor_name: Optional[str] = None


# ── Extended Company Profile ────────────────────────────────────────────────

class KeyProduct(BaseModel):
    name: str
    revenue_contribution_pct: Optional[float] = None
    description: Optional[str] = None


class ExtendedCompanyProfile(BaseModel):
    """Extended company information required for comprehensive DRHP sections."""
    # Core (matches base CompanyProfile)
    name: str
    cin: str
    pan: str
    incorporation_date: str
    registered_address: str
    sector: str
    sub_sector: Optional[str] = None
    website: Optional[str] = None
    description: str

    # Extended operational details
    employee_count: Optional[int] = None
    employee_count_year: Optional[str] = None  # "as of FY 2023-24"
    manufacturing_locations: Optional[List[str]] = None
    office_locations: Optional[List[str]] = None
    geographies_served: Optional[List[str]] = None
    key_products: Optional[List[KeyProduct]] = None
    key_customers: Optional[List[str]] = None   # Names only — no fabricated revenue split
    key_suppliers: Optional[List[str]] = None
    installed_capacity: Optional[str] = None    # e.g., "5,000 MT per annum"
    capacity_utilisation_pct: Optional[float] = None
    certifications: Optional[List[str]] = None  # e.g., ISO 9001, BIS, FSSAI
    awards: Optional[List[str]] = None
    intellectual_property: Optional[str] = None  # Description only
    business_model_description: Optional[str] = None
    competitive_strengths: Optional[List[str]] = None
    strategies: Optional[List[str]] = None
    technology_description: Optional[str] = None
    esg_summary: Optional[str] = None

    # Corporate structure
    subsidiaries: Optional[List[str]] = None
    associate_companies: Optional[List[str]] = None
    group_companies: Optional[List[str]] = None
    holding_company: Optional[str] = None

    # Statutory
    statutory_auditor: Optional[str] = None
    internal_auditor: Optional[str] = None
    legal_counsel: Optional[str] = None
    company_secretary: Optional[str] = None
    cfo_name: Optional[str] = None
    ceo_name: Optional[str] = None
    registered_office_since: Optional[str] = None
    company_type: str = "Public Limited"
    listing_exchange: Optional[str] = None    # "NSE Emerge" | "BSE SME"


# ── Extended Promoter Detail ────────────────────────────────────────────────

class ExtendedPromoterDetail(BaseModel):
    name: str
    designation: str
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    holding_pct: float = Field(..., ge=0, le=100)
    shares_held: Optional[int] = None
    dob: Optional[str] = None
    pan: Optional[str] = None
    din: Optional[str] = None              # Director Identification Number
    educational_background: Optional[str] = None
    prior_experience: Optional[str] = None
    other_directorships: Optional[List[str]] = None
    pledged_shares_pct: Optional[float] = None
    locked_in: bool = True
    lock_in_period_years: int = 3


# ── Extended Issue Details ──────────────────────────────────────────────────

class UsageItem(BaseModel):
    """Single line item in the use-of-proceeds schedule."""
    purpose: str = Field(..., description="Purpose of fund usage")
    amount_lakhs: float = Field(..., description="Amount in INR Lakhs")
    timeline_months: Optional[int] = None
    rationale: Optional[str] = None


class ExtendedIssueDetails(BaseModel):
    issue_size_cr: float
    fresh_issue_cr: float = 0.0
    ofs_cr: float = 0.0
    price_band_low: float = 0.0
    price_band_high: float
    face_value: float = 10.0
    lot_size: int = 0
    objects_of_issue: str
    use_of_proceeds: str = ""
    merchant_banker: str

    # Extended
    use_of_proceeds_structured: Optional[List[UsageItem]] = None
    pre_issue_shares: Optional[int] = None      # Total shares before issue
    fresh_issue_shares: Optional[int] = None    # New shares being issued
    ofs_shares: Optional[int] = None            # Shares offered for sale
    post_issue_shares: Optional[int] = None
    post_issue_promoter_holding_pct: Optional[float] = None
    minimum_allotment_lot: Optional[int] = None
    qib_allocation_pct: float = 0.0
    nii_allocation_pct: float = 0.0
    retail_allocation_pct: float = 100.0
    market_maker_allocation_pct: float = 5.0    # SEBI SME requirement
    underwriting: Optional[str] = None
    bid_open_date: Optional[str] = None
    bid_close_date: Optional[str] = None
    listing_date_expected: Optional[str] = None
    refund_date_expected: Optional[str] = None
    isin: Optional[str] = None
    basis_for_issue_price: Optional[str] = None


# ── Legal Proceedings ───────────────────────────────────────────────────────

class LegalProceeding(BaseModel):
    case_id: Optional[str] = None
    court_or_tribunal: str
    nature_of_case: str
    amount_involved_lakhs: Optional[float] = None
    current_status: str
    is_material: bool = False
    party_type: str = "Defendant"  # "Plaintiff" | "Defendant" | "Both"


# ── ESG Metrics ─────────────────────────────────────────────────────────────

class EsgMetrics(BaseModel):
    energy_consumption_gwh: Optional[float] = None
    water_consumption_kl: Optional[float] = None
    ghg_emissions_tco2e: Optional[float] = None
    renewable_energy_pct: Optional[float] = None
    waste_recycled_pct: Optional[float] = None
    women_employees_pct: Optional[float] = None
    csr_spend_lakhs: Optional[float] = None
    esg_rating: Optional[str] = None
    esg_rater: Optional[str] = None
    reporting_framework: Optional[str] = None


# ── Credit Rating ───────────────────────────────────────────────────────────

class CreditRating(BaseModel):
    agency: str
    rating: str
    instrument: str
    date: Optional[str] = None
    outlook: Optional[str] = None


# ── Peer Company (for benchmarking) ────────────────────────────────────────

class PeerCompany(BaseModel):
    """
    Reference company for peer comparison.
    MUST be clearly labeled as SYNTHETIC/DEMONSTRATION DATA if not from verified sources.
    """
    name: str
    exchange: str
    sector: str
    ipo_year: Optional[int] = None
    issue_size_cr: Optional[float] = None
    revenue_lakhs: Optional[float] = None
    pat_lakhs: Optional[float] = None
    pat_margin_pct: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    market_cap_cr: Optional[float] = None
    p_e_ratio: Optional[float] = None
    roe_pct: Optional[float] = None
    revenue_cagr_3yr_pct: Optional[float] = None
    data_source: str = "SYNTHETIC/DEMONSTRATION DATA"  # MUST be set explicitly
    data_verified: bool = False
    similarity_score: Optional[float] = None
    selection_rationale: Optional[str] = None


# ── Full Extended DrhpRequest v2 ────────────────────────────────────────────

class DrhpRequestV2(BaseModel):
    """
    Enterprise DRHP Request v2.
    Backward-compatible with DrhpRequest v1 — all new fields optional.
    """
    company: ExtendedCompanyProfile
    promoters: List[ExtendedPromoterDetail] = Field(default_factory=list)
    financials: List[ExtendedFinancialYear] = Field(default_factory=list, min_length=1)
    issue: ExtendedIssueDetails

    # Optional enrichment
    legal_proceedings: Optional[List[LegalProceeding]] = None
    esg_metrics: Optional[EsgMetrics] = None
    credit_ratings: Optional[List[CreditRating]] = None
    peer_companies: Optional[List[PeerCompany]] = None
    industry_overview: Optional[str] = None          # User-supplied industry text
    management_team: Optional[List[Dict[str, Any]]] = None
    material_contracts: Optional[List[str]] = None
    government_approvals: Optional[List[str]] = None

    # Pipeline control
    workspace_id: Optional[str] = None
    use_llm_generation: bool = True           # False = pure template mode (faster, safer)
    target_sections: Optional[List[str]] = None  # If None, generate all applicable
    generate_intelligence_report: bool = True
    generate_charts: bool = True
    max_peers: int = 5


# ── Pipeline Stage Results (internal types) ─────────────────────────────────

class SectionOutput(BaseModel):
    """Structured output from the LLM section generator."""
    section_id: str
    title: str
    content: str                              # Final rendered text (no raw markers)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    compliance_flags: List[str] = Field(default_factory=list)
    review_status: str = "draft"             # "draft" | "reviewed" | "approved" | "rejected"
    generation_method: str = "algorithmic"  # "llm" | "algorithmic" | "hybrid"
    llm_model: Optional[str] = None
    token_count: Optional[int] = None
    generation_time_ms: Optional[float] = None


class ConsistencyFlag(BaseModel):
    severity: str                            # "critical" | "warning" | "info"
    check_name: str
    description: str
    affected_sections: List[str]
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    recommended_fix: Optional[str] = None


class ConsistencyReport(BaseModel):
    status: str                              # "pass" | "warnings" | "critical_errors"
    errors: List[ConsistencyFlag] = Field(default_factory=list)
    warnings: List[ConsistencyFlag] = Field(default_factory=list)
    info: List[ConsistencyFlag] = Field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    can_generate_pdf: bool = True           # False only if critical errors exist


class FinancialRatio(BaseModel):
    """Single computed financial metric with full provenance."""
    name: str
    category: str
    value: Optional[float] = None
    formatted_value: str                    # "23.4%" or "Missing Information"
    formula: str
    input_values: Dict[str, Any] = Field(default_factory=dict)
    source_documents: List[str] = Field(default_factory=list)
    explanation: str
    benchmark: Optional[str] = None        # Industry average reference
    flag: Optional[str] = None             # "green" | "amber" | "red" | None
    calculation_version: str = "1.0"
    missing_inputs: List[str] = Field(default_factory=list)


class FinancialIntelligenceReport(BaseModel):
    """All computed financial metrics for a given DrhpRequest."""
    ratios: List[FinancialRatio] = Field(default_factory=list)
    growth_summary: Dict[str, Any] = Field(default_factory=dict)
    quality_scores: Dict[str, Any] = Field(default_factory=dict)
    red_flags: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    data_quality_score: float = 0.0         # 0–1, fraction of ratios with complete data
    financial_consistency_score: float = 0.0 # 0-1, consistency of historical data
    missing_data_report: List[str] = Field(default_factory=list)
    computation_time_ms: float = 0.0


class DrhpPipelineState(BaseModel):
    """
    Persisted pipeline state for resumability.
    Written to disk at end of each stage so a crashed run can resume from last checkpoint.
    """
    job_id: str
    stage: int = 0                          # Last successfully completed stage
    status: str = "pending"
    progress_pct: int = 0
    message: str = ""
    created_at: str = ""
    updated_at: str = ""
    workspace_id: Optional[str] = None
    section_states: Dict[str, str] = Field(default_factory=dict)   # section_id → status
    completed_sections: List[str] = Field(default_factory=list)
    failed_sections: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    stage_timings: Dict[str, float] = Field(default_factory=dict)   # stage_name → ms
    token_usage: Dict[str, int] = Field(default_factory=dict)
    pdf_path: Optional[str] = None
    intelligence_report_path: Optional[str] = None


# ── Extended API Response models ────────────────────────────────────────────

class DrhpJobResponseV2(BaseModel):
    job_id: str
    status: str
    message: str
    stream_url: Optional[str] = None        # SSE endpoint URL
    estimated_minutes: Optional[int] = None


class DrhpStatusResponseV2(BaseModel):
    job_id: str
    status: str                             # pending|planning|generating|reviewing|consistency|charts|pdf|intelligence|done|error
    progress_pct: int
    current_stage: Optional[str] = None
    current_section: Optional[str] = None
    message: str
    sections_completed: int = 0
    sections_total: int = 0
    consistency_status: Optional[str] = None
    compliance_status: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    drhp_ready: bool = False
    intelligence_report_ready: bool = False
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_time_seconds: Optional[float] = None
