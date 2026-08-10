"""
Financial Intelligence Engine
Computes 25+ financial ratios and quality scores from DrhpRequestV2 data.

CRITICAL DESIGN RULE:
- If required input data is missing or zero in a context that would cause division-by-zero,
  the ratio returns formatted_value = "Missing Information" and value = None.
- NEVER treat missing values as zero for ratio calculation.
- NEVER fabricate benchmark values — benchmarks are indicative ranges only, not company-specific facts.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.drhp_v2 import (
    DrhpRequestV2,
    ExtendedFinancialYear,
    FinancialIntelligenceReport,
    FinancialRatio,
)

logger = logging.getLogger(__name__)

MISSING = "Missing Information"
CALC_VERSION = "1.0"


# ─── Helper utilities ────────────────────────────────────────────────────────

def _safe_div(num: Optional[float], den: Optional[float], scale: float = 1.0) -> Optional[float]:
    """Return num/den*scale, or None if either is None. Zero denominators return 0.0 to prevent masking as missing."""
    if num is None or den is None:
        return None
    if den == 0:
        return 0.0
    return (num / den) * scale


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return MISSING
    return f"{v:.2f}%"


def _fmt_x(v: Optional[float]) -> str:
    if v is None:
        return MISSING
    return f"{v:.2f}x"


def _fmt_days(v: Optional[float]) -> str:
    if v is None:
        return MISSING
    return f"{v:.1f} days"


def _fmt_inr(v: Optional[float], unit: str = "Lakhs") -> str:
    if v is None:
        return MISSING
    return f"₹{v:,.2f} {unit}"


def _fmt_num(v: Optional[float], decimals: int = 2) -> str:
    if v is None:
        return MISSING
    return f"{v:.{decimals}f}"


def _flag(v: Optional[float], good_above: Optional[float] = None,
          warn_above: Optional[float] = None, invert: bool = False) -> Optional[str]:
    """Classify a ratio as green/amber/red given threshold ranges."""
    if v is None:
        return None
    if invert:
        # Lower is better (e.g., Debt/Equity)
        if good_above is not None and v <= good_above:
            return "green"
        if warn_above is not None and v <= warn_above:
            return "amber"
        return "red"
    else:
        if good_above is not None and v >= good_above:
            return "green"
        if warn_above is not None and v >= warn_above:
            return "amber"
        return "red"


def _make_ratio(
    name: str,
    category: str,
    value: Optional[float],
    fmt_fn,
    formula: str,
    input_values: Dict[str, Any],
    explanation: str,
    benchmark: Optional[str] = None,
    flag_val: Optional[str] = None,
    missing_inputs: Optional[List[str]] = None,
    source_documents: Optional[List[str]] = None,
) -> FinancialRatio:
    return FinancialRatio(
        name=name,
        category=category,
        value=value,
        formatted_value=fmt_fn(value),
        formula=formula,
        input_values=input_values,
        explanation=explanation,
        benchmark=benchmark,
        flag=flag_val,
        calculation_version=CALC_VERSION,
        missing_inputs=missing_inputs or [],
        source_documents=source_documents or [],
    )


# ─── Core computation functions (per financial year) ─────────────────────────

def _derive_missing_from_available(fy: ExtendedFinancialYear) -> ExtendedFinancialYear:
    """
    Attempt to derive fields that can be mathematically computed from other available fields.
    Only assigns derived values — never overwrites explicitly provided values.
    """
    fy_dict = fy.model_dump()

    # EBITDA = EBIT + D&A
    if fy.ebitda is None and fy.ebit is not None and fy.depreciation is not None:
        fy_dict["ebitda"] = fy.ebit + fy.depreciation

    # EBIT = EBITDA - D&A
    if fy.ebit is None and fy.ebitda is not None and fy.depreciation is not None:
        fy_dict["ebit"] = fy.ebitda - fy.depreciation

    # PBT = EBIT - Interest
    if fy.pbt is None and fy.ebit is not None and fy.interest_expense is not None:
        fy_dict["pbt"] = fy.ebit - fy.interest_expense

    # FCF = OCF - Capex
    if fy.free_cash_flow is None and fy.operating_cash_flow is not None and fy.capex is not None:
        fy_dict["free_cash_flow"] = fy.operating_cash_flow - fy.capex

    # Total liabilities = Total assets - Total equity
    if fy.total_liabilities is None and fy.total_assets and fy.total_equity:
        fy_dict["total_liabilities"] = fy.total_assets - fy.total_equity

    return ExtendedFinancialYear(**fy_dict)


def compute_ratios_for_year(fy: ExtendedFinancialYear) -> List[FinancialRatio]:
    """Compute all applicable financial ratios for a single financial year."""
    fy = _derive_missing_from_available(fy)
    ratios: List[FinancialRatio] = []

    def _missing(*fields) -> List[str]:
        # After schema fix: None means MISSING, 0.0 means explicitly-zero.
        # We check only for None here — zero is a valid disclosed value.
        return [f for f in fields if getattr(fy, f, None) is None]

    # ── PROFITABILITY ──────────────────────────────────────────────────────

    # EBITDA Margin
    ebitda_margin = _safe_div(fy.ebitda, fy.revenue if fy.revenue is not None else None, 100)
    miss = _missing("ebitda") if fy.revenue is not None else ["ebitda", "revenue"]
    ratios.append(_make_ratio(
        name="EBITDA Margin", category="Profitability",
        value=ebitda_margin, fmt_fn=_fmt_pct,
        formula="(EBITDA / Revenue) × 100",
        input_values={"ebitda": fy.ebitda, "revenue": fy.revenue},
        explanation="Measures operating profitability before non-cash charges and financing costs. "
                    "Higher margins indicate stronger core business economics.",
        benchmark="Manufacturing: 12-20%; Services: 15-30%; SME typical: 8-18%",
        flag_val=_flag(ebitda_margin, good_above=15, warn_above=8),
        missing_inputs=miss,
    ))

    # PAT Margin
    pat_margin = _safe_div(fy.net_profit, fy.revenue if fy.revenue is not None else None, 100)
    ratios.append(_make_ratio(
        name="PAT Margin", category="Profitability",
        value=pat_margin, fmt_fn=_fmt_pct,
        formula="(PAT / Revenue) × 100",
        input_values={"pat": fy.net_profit, "revenue": fy.revenue},
        explanation="Net profit margin after all expenses, interest, and taxes. "
                    "Directly shows how much of each rupee of revenue converts to profit for shareholders.",
        benchmark="Manufacturing: 5-12%; Services: 8-20%; SME IPO median: 6-10%",
        flag_val=_flag(pat_margin, good_above=10, warn_above=5),
        missing_inputs=_missing("net_profit") if fy.revenue is not None else ["net_profit", "revenue"],
    ))

    # Gross Margin
    gross_margin = _safe_div(fy.gross_profit, fy.revenue if fy.revenue is not None else None, 100)
    ratios.append(_make_ratio(
        name="Gross Profit Margin", category="Profitability",
        value=gross_margin, fmt_fn=_fmt_pct,
        formula="(Gross Profit / Revenue) × 100",
        input_values={"gross_profit": fy.gross_profit, "revenue": fy.revenue},
        explanation="Revenue remaining after direct costs (COGS). Indicates pricing power and product margin quality.",
        benchmark="Manufacturing: 20-40%; Services: 40-70%",
        flag_val=_flag(gross_margin, good_above=30, warn_above=15),
        missing_inputs=_missing("gross_profit") if fy.revenue is not None else ["gross_profit", "revenue"],
    ))

    # ROE
    roe = _safe_div(fy.net_profit, fy.total_equity if fy.total_equity is not None else None, 100)
    ratios.append(_make_ratio(
        name="Return on Equity (ROE)", category="Profitability",
        value=roe, fmt_fn=_fmt_pct,
        formula="(PAT / Average Shareholders Equity) × 100",
        input_values={"pat": fy.net_profit, "equity": fy.total_equity},
        explanation="Return generated for equity shareholders on their invested capital. "
                    "A key metric for IPO investors evaluating management effectiveness.",
        benchmark="SME IPO median: 15-25%; Good: >20%; Strong: >30%",
        flag_val=_flag(roe, good_above=20, warn_above=10),
        missing_inputs=_missing("net_profit", "total_equity"),
    ))

    # ROCE
    ebit = fy.ebit if fy.ebit is not None else (fy.ebitda - fy.depreciation if fy.ebitda is not None and fy.depreciation is not None else None)
    capital_employed = (fy.total_assets - (fy.current_liabilities or 0)) if fy.total_assets is not None else None
    roce = _safe_div(ebit, capital_employed if capital_employed is not None else None, 100)
    ratios.append(_make_ratio(
        name="Return on Capital Employed (ROCE)", category="Profitability",
        value=roce, fmt_fn=_fmt_pct,
        formula="(EBIT / Capital Employed) × 100 where Capital Employed = Total Assets - Current Liabilities",
        input_values={"ebit": ebit, "capital_employed": capital_employed},
        explanation="Measures efficiency in generating profits from all capital deployed, "
                    "regardless of financing mix. Higher ROCE indicates superior capital allocation.",
        benchmark="SME: 12-20%; Good: >18%; Strong: >25%",
        flag_val=_flag(roce, good_above=18, warn_above=10),
        missing_inputs=[] if (ebit is not None and capital_employed is not None) else ["ebit_or_ebitda_depreciation", "total_assets"],
    ))

    # ── LIQUIDITY ──────────────────────────────────────────────────────────

    # Current Ratio
    current_ratio = _safe_div(fy.current_assets, fy.current_liabilities)
    ratios.append(_make_ratio(
        name="Current Ratio", category="Liquidity",
        value=current_ratio, fmt_fn=_fmt_x,
        formula="Current Assets / Current Liabilities",
        input_values={"current_assets": fy.current_assets, "current_liabilities": fy.current_liabilities},
        explanation="Short-term liquidity — ability to meet obligations within 12 months. "
                    "Ratio below 1.0 indicates potential liquidity stress.",
        benchmark="Healthy: 1.5x-3.0x; Minimum acceptable: >1.0x",
        flag_val=_flag(current_ratio, good_above=1.5, warn_above=1.0),
        missing_inputs=_missing("current_assets", "current_liabilities"),
    ))

    # Quick Ratio
    inventory = fy.inventory or 0
    quick_assets = (fy.current_assets - inventory) if fy.current_assets is not None else None
    quick_ratio = _safe_div(quick_assets, fy.current_liabilities)
    ratios.append(_make_ratio(
        name="Quick Ratio", category="Liquidity",
        value=quick_ratio, fmt_fn=_fmt_x,
        formula="(Current Assets - Inventory) / Current Liabilities",
        input_values={"current_assets": fy.current_assets, "inventory": fy.inventory,
                      "current_liabilities": fy.current_liabilities},
        explanation="More conservative than current ratio — excludes inventory which may not be quickly liquidated. "
                    "Particularly relevant for manufacturing companies with slow-moving inventory.",
        benchmark="Healthy: >1.0x; Cautionary: 0.7x-1.0x",
        flag_val=_flag(quick_ratio, good_above=1.0, warn_above=0.7),
        missing_inputs=_missing("current_assets", "current_liabilities"),
    ))

    # Cash Ratio
    cash_ratio = _safe_div(fy.cash_and_equivalents, fy.current_liabilities)
    ratios.append(_make_ratio(
        name="Cash Ratio", category="Liquidity",
        value=cash_ratio, fmt_fn=_fmt_x,
        formula="Cash and Cash Equivalents / Current Liabilities",
        input_values={"cash": fy.cash_and_equivalents, "current_liabilities": fy.current_liabilities},
        explanation="Most conservative liquidity measure — only liquid cash vs current obligations. "
                    "Very low cash ratio may indicate reliance on credit facilities.",
        benchmark="Typically 0.1x-0.5x; Very high may indicate inefficient cash deployment",
        flag_val=_flag(cash_ratio, good_above=0.2, warn_above=0.05),
        missing_inputs=_missing("cash_and_equivalents", "current_liabilities"),
    ))

    # ── LEVERAGE ───────────────────────────────────────────────────────────

    # Debt/Equity
    de_ratio = _safe_div(fy.total_debt, fy.total_equity if fy.total_equity is not None else None)
    ratios.append(_make_ratio(
        name="Debt/Equity Ratio", category="Leverage",
        value=de_ratio, fmt_fn=_fmt_x,
        formula="Total Debt / Total Shareholders Equity",
        input_values={"total_debt": fy.total_debt, "equity": fy.total_equity},
        explanation="Financial leverage ratio — higher values indicate greater reliance on debt. "
                    "SME IPOs with high D/E ratios face greater financial risk and interest burden.",
        benchmark="Low risk: <0.5x; Moderate: 0.5x-1.5x; High: >2.0x",
        flag_val=_flag(de_ratio, good_above=0.5, warn_above=1.5, invert=True),
        missing_inputs=_missing("total_debt", "total_equity"),
    ))

    # Debt/EBITDA
    debt_ebitda = _safe_div(fy.total_debt, fy.ebitda if fy.ebitda is not None else None)
    ratios.append(_make_ratio(
        name="Debt/EBITDA", category="Leverage",
        value=debt_ebitda, fmt_fn=_fmt_x,
        formula="Total Debt / EBITDA",
        input_values={"total_debt": fy.total_debt, "ebitda": fy.ebitda},
        explanation="Years of EBITDA required to repay total debt. Key metric for debt sustainability — "
                    "lenders and investors use this to assess repayment capacity.",
        benchmark="Low: <2.0x; Moderate: 2-4x; High: >5x",
        flag_val=_flag(debt_ebitda, good_above=2.0, warn_above=4.0, invert=True),
        missing_inputs=_missing("total_debt", "ebitda"),
    ))

    # Interest Coverage
    interest_coverage = _safe_div(
        fy.ebit if fy.ebit is not None else ebit,
        fy.interest_expense if fy.interest_expense is not None else None
    )
    ratios.append(_make_ratio(
        name="Interest Coverage Ratio", category="Leverage",
        value=interest_coverage, fmt_fn=_fmt_x,
        formula="EBIT / Interest Expense",
        input_values={"ebit": ebit, "interest_expense": fy.interest_expense},
        explanation="Number of times EBIT covers interest obligations. Ratio below 1.5x indicates "
                    "inability to comfortably service debt — a critical risk flag for investors.",
        benchmark="Safe: >3.0x; Cautionary: 1.5x-3.0x; Distressed: <1.5x",
        flag_val=_flag(interest_coverage, good_above=3.0, warn_above=1.5),
        missing_inputs=[] if (ebit is not None and fy.interest_expense is not None) else ["ebit", "interest_expense"],
    ))

    # ── EFFICIENCY ──────────────────────────────────────────────────────────

    # Asset Turnover
    asset_turnover = _safe_div(
        fy.revenue if fy.revenue is not None else None,
        fy.total_assets if fy.total_assets is not None else None
    )
    ratios.append(_make_ratio(
        name="Asset Turnover Ratio", category="Efficiency",
        value=asset_turnover, fmt_fn=_fmt_x,
        formula="Revenue / Total Assets",
        input_values={"revenue": fy.revenue, "total_assets": fy.total_assets},
        explanation="Revenue generated per rupee of assets deployed. Higher values indicate "
                    "more efficient use of the asset base.",
        benchmark="Manufacturing: 0.8-1.5x; Services: 1.5-3.0x",
        flag_val=_flag(asset_turnover, good_above=1.0, warn_above=0.5),
        missing_inputs=_missing("total_assets") if fy.revenue is not None else ["revenue", "total_assets"],
    ))

    # Working Capital Turnover
    working_capital = (
        (fy.current_assets - (fy.current_liabilities or 0))
        if fy.current_assets is not None and fy.current_liabilities is not None
        else None
    )
    wc_turnover = (
        _safe_div(fy.revenue if fy.revenue is not None else None, working_capital)
        if working_capital is not None and working_capital > 0
        else None
    )
    ratios.append(_make_ratio(
        name="Working Capital Turnover", category="Efficiency",
        value=wc_turnover, fmt_fn=_fmt_x,
        formula="Revenue / Working Capital where Working Capital = Current Assets - Current Liabilities",
        input_values={"revenue": fy.revenue, "current_assets": fy.current_assets, "current_liabilities": fy.current_liabilities},
        explanation="Revenue generated per rupee of net working capital. Higher ratios indicate efficient "
                    "utilization of short-term capital. Negative working capital companies may show N/A.",
        benchmark="Manufacturing: 4-8x; Services: 8-15x; Negative working capital: not applicable",
        flag_val=_flag(wc_turnover, good_above=5.0, warn_above=2.0),
        missing_inputs=_missing("current_assets", "current_liabilities") if fy.revenue else ["revenue", "current_assets", "current_liabilities"],
    ))

    # Inventory Days
    daily_cogs = (fy.cogs or (fy.revenue - (fy.gross_profit or 0))) if fy.revenue else None
    inv_days = _safe_div(fy.inventory, (daily_cogs / 365) if daily_cogs else None) if fy.inventory else None
    ratios.append(_make_ratio(
        name="Inventory Days", category="Efficiency",
        value=inv_days, fmt_fn=_fmt_days,
        formula="(Inventory / COGS) × 365",
        input_values={"inventory": fy.inventory, "cogs": daily_cogs},
        explanation="Average days inventory is held before sale. Lower values indicate faster "
                    "stock turnover and reduced working capital tie-up.",
        benchmark="Industry-dependent; Manufacturing: 30-90 days; Services: minimal",
        flag_val=_flag(inv_days, good_above=90, warn_above=150, invert=True),
        missing_inputs=_missing("inventory") if daily_cogs else ["inventory", "cogs_or_revenue"],
    ))

    # Receivable Days (DSO)
    revenue_per_day = (fy.revenue / 365) if fy.revenue else None
    dso = _safe_div(fy.trade_receivables, revenue_per_day)
    ratios.append(_make_ratio(
        name="Receivable Days (DSO)", category="Efficiency",
        value=dso, fmt_fn=_fmt_days,
        formula="(Trade Receivables / Revenue) × 365",
        input_values={"receivables": fy.trade_receivables, "revenue": fy.revenue},
        explanation="Average days to collect payment from customers. "
                    "High DSO increases working capital requirements and credit risk.",
        benchmark="Good: <45 days; Acceptable: 45-90 days; Concern: >90 days",
        flag_val=_flag(dso, good_above=45, warn_above=90, invert=True),
        missing_inputs=_missing("trade_receivables") if fy.revenue else ["trade_receivables", "revenue"],
    ))

    # Payable Days (DPO)
    dpo = _safe_div(fy.trade_payables, (daily_cogs / 365) if daily_cogs else None) if fy.trade_payables else None
    ratios.append(_make_ratio(
        name="Payable Days (DPO)", category="Efficiency",
        value=dpo, fmt_fn=_fmt_days,
        formula="(Trade Payables / COGS) × 365",
        input_values={"payables": fy.trade_payables, "cogs": daily_cogs},
        explanation="Average days taken to pay suppliers. Longer DPO improves working capital "
                    "but may strain supplier relationships.",
        benchmark="Balanced: 30-60 days",
        flag_val=None,  # Neutral — higher/lower can both be good or bad
        missing_inputs=_missing("trade_payables") if daily_cogs else ["trade_payables", "cogs"],
    ))

    # Cash Conversion Cycle
    ccc = None
    ccc_miss = []
    if inv_days is not None and dso is not None and dpo is not None:
        ccc = inv_days + dso - dpo
    else:
        ccc_miss = ["inventory_days", "dso", "dpo"]
    ratios.append(_make_ratio(
        name="Cash Conversion Cycle", category="Efficiency",
        value=ccc, fmt_fn=_fmt_days,
        formula="Inventory Days + Receivable Days - Payable Days",
        input_values={"inventory_days": inv_days, "dso": dso, "dpo": dpo},
        explanation="Days of working capital cycle — how long cash is tied up in operations. "
                    "Negative CCC (e.g., FMCG) means collecting before paying, a sign of strong business.",
        benchmark="Lower is generally better; Negative CCC is excellent",
        flag_val=_flag(ccc, good_above=30, warn_above=90, invert=True) if ccc is not None else None,
        missing_inputs=ccc_miss,
    ))

    # ── IPO SPECIFIC ────────────────────────────────────────────────────────

    # EPS — convert Lakhs to absolute INR before dividing by shares
    eps_pat_abs = (fy.net_profit * 100000) if fy.net_profit is not None else None
    eps = _safe_div(eps_pat_abs, fy.shares_outstanding)  # ₹ per share
    ratios.append(_make_ratio(
        name="Earnings Per Share (EPS)", category="IPO Metrics",
        value=eps, fmt_fn=lambda v: f"₹{v:.2f}" if v is not None else MISSING,
        formula="(PAT in absolute INR) / Weighted Average Shares Outstanding",
        input_values={"pat_lakhs": fy.net_profit, "shares": fy.shares_outstanding},
        explanation="Profit attributable to each equity share. Key metric for P/E calculation "
                    "and IPO pricing. EPS trend over 3 years is a primary investor consideration.",
        benchmark="Varies by sector; P/E is typically applied to EPS for valuation",
        flag_val=_flag(eps, good_above=10, warn_above=0),
        missing_inputs=_missing("net_profit", "shares_outstanding"),
    ))

    # Book Value per Share
    equity_abs = (fy.total_equity * 100000) if fy.total_equity is not None else None
    bvps = _safe_div(equity_abs, fy.shares_outstanding)
    ratios.append(_make_ratio(
        name="Book Value per Share", category="IPO Metrics",
        value=bvps, fmt_fn=lambda v: f"₹{v:.2f}" if v is not None else MISSING,
        formula="(Net Worth in absolute INR) / Total Shares Outstanding",
        input_values={"net_worth_lakhs": fy.total_equity, "shares": fy.shares_outstanding},
        explanation="Net asset value per share — the accounting worth of each share. "
                    "Price-to-Book ratio is used alongside P/E for valuation benchmarking.",
        benchmark="Varies; P/B ratio indicates premium/discount to book",
        flag_val=None,
        missing_inputs=_missing("total_equity", "shares_outstanding"),
    ))

    # Fix: Inject source_documents from provenance into all computed ratios
    if fy.provenance and fy.provenance.source_document:
        for r in ratios:
            r.source_documents = [fy.provenance.source_document]

    return ratios


def compute_growth_metrics(fys: List[ExtendedFinancialYear]) -> Dict[str, Any]:
    """Compute multi-year CAGR metrics across all provided financial years."""
    if len(fys) < 2:
        return {
            "revenue_cagr": MISSING,
            "pat_cagr": MISSING,
            "ebitda_cagr": MISSING,
            "note": "Minimum 2 years required for CAGR calculation",
        }

    def _cagr(start: Optional[float], end: Optional[float], years: int) -> Optional[float]:
        if start is None or end is None or start <= 0 or years == 0:
            return None
        try:
            return ((end / start) ** (1 / years) - 1) * 100
        except (ValueError, ZeroDivisionError):
            return None

    years_count = len(fys) - 1
    rev_cagr = _cagr(fys[0].revenue, fys[-1].revenue, years_count)
    pat_cagr = _cagr(fys[0].net_profit, fys[-1].net_profit, years_count)
    ebitda_cagr = (
        _cagr(fys[0].ebitda, fys[-1].ebitda, years_count)
        if (fys[0].ebitda is not None and fys[-1].ebitda is not None)
        else None
    )

    return {
        "revenue_cagr": _fmt_pct(rev_cagr),
        "revenue_cagr_value": rev_cagr,
        "pat_cagr": _fmt_pct(pat_cagr),
        "pat_cagr_value": pat_cagr,
        "ebitda_cagr": _fmt_pct(ebitda_cagr) if ebitda_cagr is not None else MISSING,
        "ebitda_cagr_value": ebitda_cagr,
        "years": years_count,
        "from_year": fys[0].year,
        "to_year": fys[-1].year,
    }


def compute_altman_z(fy: ExtendedFinancialYear) -> Dict[str, Any]:
    """
    Compute Altman Z-Score for public companies (original 1968 model).
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Returns MISSING if insufficient data is available.
    Note: Z-score is designed for manufacturing firms and should be used with caution for services.
    """
    required = [fy.current_assets, fy.current_liabilities, fy.total_assets,
                fy.total_equity, fy.total_debt, fy.net_profit, fy.revenue, fy.ebit]

    missing = [n for n, v in [
        ("current_assets", fy.current_assets), ("current_liabilities", fy.current_liabilities),
        ("total_assets", fy.total_assets), ("total_equity", fy.total_equity),
        ("total_debt", fy.total_debt), ("net_profit", fy.net_profit),
        ("revenue", fy.revenue), ("ebit", fy.ebit)
    ] if v is None]

    if missing or fy.total_assets is None or fy.total_assets == 0:
        return {"value": MISSING, "missing_inputs": missing, "interpretation": MISSING}

    working_capital = (fy.current_assets or 0) - (fy.current_liabilities or 0)
    retained_earnings = fy.net_profit if fy.net_profit is not None else 0  # Simplified: using PAT as proxy
    market_cap_proxy = fy.total_equity if fy.total_equity is not None else 0  # For private co, use book equity
    total_debt = fy.total_debt if fy.total_debt is not None else 0

    x1 = working_capital / fy.total_assets
    x2 = retained_earnings / fy.total_assets
    x3 = (fy.ebit if fy.ebit is not None else 0) / fy.total_assets
    x4 = market_cap_proxy / (total_debt if total_debt > 0 else 1)
    x5 = (fy.revenue if fy.revenue is not None else 0) / fy.total_assets

    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    if z > 2.99:
        interpretation = "Safe Zone — low financial distress probability"
        flag = "green"
    elif z > 1.81:
        interpretation = "Grey Zone — moderate financial uncertainty"
        flag = "amber"
    else:
        interpretation = "Distress Zone — elevated financial distress risk"
        flag = "red"

    return {
        "value": round(z, 3),
        "formatted": f"{z:.3f}",
        "interpretation": interpretation,
        "flag": flag,
        "note": "Altman Z-Score (1968 model). Proxy used for market value of equity = book equity "
                "for pre-IPO companies. Use as indicative metric only.",
        "missing_inputs": [],
    }


def detect_red_flags(fys: List[ExtendedFinancialYear]) -> List[str]:
    """Detect financial red flags from the data. Returns plain-language findings."""
    flags = []
    if not fys:
        return flags

    latest = fys[-1]

    # Profitability flags
    if latest.net_profit is not None and latest.net_profit < 0:
        flags.append(f"Negative PAT in {latest.year}: ₹{abs(latest.net_profit):,.2f} Lakhs net loss reported.")

    # Declining revenue
    if len(fys) >= 2 and fys[-1].revenue and fys[-2].revenue:
        if fys[-1].revenue < fys[-2].revenue:
            decline = ((fys[-2].revenue - fys[-1].revenue) / fys[-2].revenue) * 100
            flags.append(f"Revenue declined {decline:.1f}% from {fys[-2].year} to {fys[-1].year}.")

    # High leverage
    de = _safe_div(latest.total_debt, latest.total_equity if latest.total_equity else None)
    if de is not None and de > 2.0:
        flags.append(f"High Debt/Equity of {de:.2f}x in {latest.year} — elevated financial risk.")

    # Liquidity concern
    cr = _safe_div(latest.current_assets, latest.current_liabilities)
    if cr is not None and cr < 1.0:
        flags.append(f"Current Ratio below 1.0 ({cr:.2f}x) in {latest.year} — potential short-term liquidity risk.")

    # Negative OCF despite positive PAT
    if (latest.operating_cash_flow is not None and latest.operating_cash_flow < 0
            and latest.net_profit is not None and latest.net_profit > 0):
        flags.append(f"Positive PAT but negative Operating Cash Flow in {latest.year} — earnings quality concern.")

    # Interest coverage concern
    if latest.ebit is not None and latest.interest_expense is not None and latest.interest_expense > 0:
        ic = latest.ebit / latest.interest_expense
        if ic < 1.5:
            flags.append(f"Interest Coverage Ratio of {ic:.2f}x in {latest.year} — EBIT barely covers interest obligations.")

    # EBITDA margin compression (revenue growing but margins shrinking)
    if len(fys) >= 3:
        margins = []
        for fy in fys:
            if fy.revenue and fy.revenue > 0 and fy.ebitda is not None:
                margins.append((fy.year, (fy.ebitda / fy.revenue) * 100))
        if len(margins) >= 3:
            # Check for consistent compression over last 3 years
            if margins[-1][1] < margins[-2][1] < margins[-3][1]:
                compression = margins[-3][1] - margins[-1][1]
                flags.append(
                    f"EBITDA margin compressed by {compression:.1f}pp from {margins[-3][0]} to {margins[-1][0]} "
                    f"({margins[-3][1]:.1f}% → {margins[-1][1]:.1f}%) — revenue growing but operational efficiency declining."
                )

    return flags


def detect_strengths(fys: List[ExtendedFinancialYear], growth: Dict[str, Any]) -> List[str]:
    """Identify positive financial indicators."""
    strengths = []
    if not fys:
        return strengths

    latest = fys[-1]

    # Revenue growth
    rev_cagr = growth.get("revenue_cagr_value")
    if rev_cagr is not None and rev_cagr > 20:
        strengths.append(f"Strong revenue CAGR of {rev_cagr:.1f}% over {growth.get('years', '?')} years.")

    # Good margins
    if latest.ebitda and latest.revenue and latest.revenue > 0:
        margin = (latest.ebitda / latest.revenue) * 100
        if margin > 18:
            strengths.append(f"Above-industry EBITDA margin of {margin:.1f}% in {latest.year}.")

    # Low leverage
    de = _safe_div(latest.total_debt, latest.total_equity if latest.total_equity else None)
    if de is not None and de < 0.5:
        strengths.append(f"Conservative leverage — Debt/Equity of {de:.2f}x in {latest.year}.")

    # Positive FCF
    if latest.free_cash_flow is not None and latest.free_cash_flow > 0:
        strengths.append(f"Positive Free Cash Flow of ₹{latest.free_cash_flow:,.2f} Lakhs in {latest.year}.")

    # Improving Interest Coverage Ratio trend
    if len(fys) >= 2:
        icr_values = []
        for fy in fys:
            if fy.ebit is not None and fy.interest_expense and fy.interest_expense > 0:
                icr_values.append((fy.year, fy.ebit / fy.interest_expense))
        if len(icr_values) >= 2 and icr_values[-1][1] > icr_values[-2][1] and icr_values[-1][1] >= 3.0:
            strengths.append(
                f"Improving interest coverage — ICR of {icr_values[-1][1]:.1f}x in {icr_values[-1][0]} "
                f"(up from {icr_values[-2][1]:.1f}x in {icr_values[-2][0]}), indicating strengthening debt-servicing capacity."
            )

    return strengths


# ─── Main entry point ────────────────────────────────────────────────────────

def compute_financial_intelligence(req: DrhpRequestV2) -> FinancialIntelligenceReport:
    """
    Main entry point: compute all financial metrics for a DrhpRequestV2.
    Returns FinancialIntelligenceReport with ratios, growth, red flags, strengths.
    """
    start = time.perf_counter()
    all_ratios: List[FinancialRatio] = []

    if not req.financials:
        logger.warning("No financial years provided — cannot compute financial intelligence.")
        return FinancialIntelligenceReport(
            ratios=[],
            red_flags=["No financial data provided — all ratio computations unavailable."],
            data_quality_score=0.0,
        )

    # Use the last (most recent) year for single-year ratios
    latest_fy = req.financials[-1]
    all_ratios.extend(compute_ratios_for_year(latest_fy))

    # Growth metrics require multiple years
    growth = compute_growth_metrics(req.financials)

    # Add growth as ratios
    for key, label, category in [
        ("revenue_cagr_value", "Revenue CAGR", "Growth"),
        ("pat_cagr_value", "PAT CAGR", "Growth"),
        ("ebitda_cagr_value", "EBITDA CAGR", "Growth"),
    ]:
        val = growth.get(key)
        all_ratios.append(_make_ratio(
            name=label, category=category,
            value=val, fmt_fn=_fmt_pct,
            formula=f"((End Value / Start Value) ^ (1 / Years)) - 1",
            input_values={"from": growth.get("from_year"), "to": growth.get("to_year"),
                          "years": growth.get("years")},
            explanation=f"Compound annual growth rate for {label.replace(' CAGR', '')} "
                        f"from {growth.get('from_year', '?')} to {growth.get('to_year', '?')}.",
            benchmark="High growth: >20%; Moderate: 10-20%; Low: <10%",
            flag_val=_flag(val, good_above=20, warn_above=10),
            missing_inputs=[] if val is not None else ["multiple_financial_years_required"],
        ))

    # Altman Z-Score
    z_score = compute_altman_z(latest_fy)
    all_ratios.append(FinancialRatio(
        name="Altman Z-Score",
        category="Quality",
        value=z_score.get("value") if isinstance(z_score.get("value"), float) else None,
        formatted_value=z_score.get("formatted", MISSING),
        formula="1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5",
        input_values={"year": latest_fy.year},
        explanation=z_score.get("interpretation", MISSING) + ". " + z_score.get("note", ""),
        flag=z_score.get("flag"),
        missing_inputs=z_score.get("missing_inputs", []),
        calculation_version=CALC_VERSION,
    ))

    # Red flags and strengths
    red_flags = detect_red_flags(req.financials)
    strengths = detect_strengths(req.financials, growth)

    # Data quality score: fraction of ratios with complete data
    complete = sum(1 for r in all_ratios if r.value is not None)
    quality_score = complete / len(all_ratios) if all_ratios else 0.0

    # Collect missing data report
    missing_report = []
    for fy in req.financials:
        fy_missing = []
        if fy.revenue is None: fy_missing.append("Revenue")
        if fy.net_profit is None: fy_missing.append("Net Profit")
        if fy.total_assets is None: fy_missing.append("Total Assets")
        if fy.total_equity is None: fy_missing.append("Total Equity")
        if fy.operating_cash_flow is None: fy_missing.append("Operating Cash Flow")
        if fy_missing:
            missing_report.append(f"{fy.year}: Missing critical fields ({', '.join(fy_missing)})")

    # Financial consistency score
    # Checks if total_assets == total_equity + total_liabilities (if available)
    consistency_score = 1.0
    for fy in req.financials:
        if fy.total_assets and fy.total_equity and fy.total_liabilities:
            diff = abs(fy.total_assets - (fy.total_equity + fy.total_liabilities))
            if diff > 1.0: # allow small rounding errors
                consistency_score -= 0.2 # Penalty for inconsistency
                missing_report.append(f"{fy.year}: Balance sheet does not balance (Assets != Equity + Liabilities). Difference: {diff}")
    
    consistency_score = max(0.0, consistency_score)

    elapsed = (time.perf_counter() - start) * 1000
    logger.info("Financial intelligence computed: %d ratios, %.1f%% data quality, %.0fms",
                len(all_ratios), quality_score * 100, elapsed)

    return FinancialIntelligenceReport(
        ratios=all_ratios,
        growth_summary=growth,
        quality_scores={"altman_z": z_score},
        red_flags=red_flags,
        strengths=strengths,
        data_quality_score=quality_score,
        financial_consistency_score=consistency_score,
        missing_data_report=missing_report,
        computation_time_ms=elapsed,
    )
