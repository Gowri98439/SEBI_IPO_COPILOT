"""
conftest.py — Shared pytest fixtures for the SEBI IPO Copilot test suite.

Provides reusable instances of:
- ExtendedFinancialYear (single-year, multi-year)
- DrhpRequestV2 (minimal valid payload + fully-populated payload)
- ConsistencyEngine-compatible payload
"""

import pytest
from app.schemas.drhp_v2 import (
    DrhpRequestV2,
    ExtendedFinancialYear,
    ExtendedCompanyProfile,
    ExtendedPromoterDetail,
    ExtendedIssueDetails,
)


# ── Financial Year fixtures ──────────────────────────────────────────────────

@pytest.fixture
def fy_complete():
    """A fully-populated ExtendedFinancialYear — all ratio-required fields set."""
    return ExtendedFinancialYear(
        year="2023-24",
        revenue=6500.0,
        gross_profit=2600.0,
        ebitda=1180.0,
        depreciation=180.0,
        ebit=1000.0,
        interest_expense=120.0,
        pbt=880.0,
        tax_expense=220.0,
        net_profit=660.0,
        total_assets=9800.0,
        current_assets=4200.0,
        cash_and_equivalents=800.0,
        inventory=600.0,
        trade_receivables=1800.0,
        fixed_assets=5600.0,
        capex=400.0,
        total_equity=4800.0,
        total_debt=2500.0,
        long_term_debt=1800.0,
        short_term_debt=700.0,
        current_liabilities=2500.0,
        trade_payables=900.0,
        total_liabilities=5000.0,
        operating_cash_flow=900.0,
        investing_cash_flow=-400.0,
        financing_cash_flow=-300.0,
        free_cash_flow=500.0,
        shares_outstanding=5000000,
        face_value_per_share=10.0,
    )


@pytest.fixture
def fy_minimal():
    """A minimal ExtendedFinancialYear — only the fields required by the schema."""
    return ExtendedFinancialYear(
        year="2023-24",
        revenue=3000.0,
        net_profit=300.0,
        total_assets=5000.0,
        total_equity=2000.0,
    )


@pytest.fixture
def fy_loss():
    """A year with a net loss and negative OCF."""
    return ExtendedFinancialYear(
        year="2022-23",
        revenue=2000.0,
        ebitda=-100.0,
        net_profit=-250.0,
        total_assets=4000.0,
        total_equity=1500.0,
        total_debt=2500.0,
        current_assets=1000.0,
        current_liabilities=1200.0,
        operating_cash_flow=-180.0,
        ebit=-280.0,
        interest_expense=200.0,
    )


@pytest.fixture
def three_year_financials():
    """Three consecutive financial years — required for CAGR tests."""
    return [
        ExtendedFinancialYear(
            year="2021-22",
            revenue=3200.0, net_profit=180.0, total_assets=5500.0, total_equity=2800.0,
            ebitda=480.0, depreciation=80.0, ebit=400.0, interest_expense=60.0,
            current_assets=2200.0, current_liabilities=1400.0,
        ),
        ExtendedFinancialYear(
            year="2022-23",
            revenue=4800.0, net_profit=380.0, total_assets=7200.0, total_equity=3600.0,
            ebitda=820.0, depreciation=130.0, ebit=690.0, interest_expense=90.0,
            current_assets=3000.0, current_liabilities=1800.0,
        ),
        ExtendedFinancialYear(
            year="2023-24",
            revenue=6500.0, net_profit=660.0, total_assets=9800.0, total_equity=4800.0,
            ebitda=1180.0, depreciation=180.0, ebit=1000.0, interest_expense=120.0,
            current_assets=4200.0, current_liabilities=2500.0,
        ),
    ]


# ── Company / Issue / Promoter fixtures ────────────────────────────────────

@pytest.fixture
def valid_company():
    return ExtendedCompanyProfile(
        name="Acme Technologies Private Limited",
        cin="U72900MH2020PTC123456",
        pan="AABCT1234A",
        incorporation_date="2020-01-15",
        registered_address="123 Business Park, Andheri East, Mumbai 400069",
        sector="Technology",
        description=(
            "Acme Technologies is a Mumbai-based cloud software company providing SaaS "
            "solutions to BFSI and logistics sectors. Founded in 2020, the company has grown "
            "revenues at a CAGR exceeding 40% over three financial years."
        ),
    )


@pytest.fixture
def valid_promoters():
    return [
        ExtendedPromoterDetail(name="Rahul Sharma", designation="MD", holding_pct=55.0),
        ExtendedPromoterDetail(name="Priya Singh",  designation="ED", holding_pct=20.0),
    ]


@pytest.fixture
def valid_issue():
    return ExtendedIssueDetails(
        issue_size_cr=18.0,
        fresh_issue_cr=12.0,
        ofs_cr=6.0,
        price_band_low=120.0,
        price_band_high=128.0,
        face_value=10.0,
        lot_size=1000,
        objects_of_issue=(
            "1. Expansion of cloud infrastructure — ₹6 Cr\n"
            "2. Working capital requirements — ₹4 Cr\n"
            "3. General corporate purposes — ₹2 Cr"
        ),
        merchant_banker="Axis Capital Limited",
    )


@pytest.fixture
def valid_drhp_request(valid_company, valid_promoters, valid_issue, three_year_financials):
    """A fully-valid DrhpRequestV2 — passes all 20 consistency checks."""
    return DrhpRequestV2(
        company=valid_company,
        promoters=valid_promoters,
        financials=three_year_financials,
        issue=valid_issue,
    )
