"""
test_consistency_engine.py
Unit tests for app/ai/consistency_engine.py

Coverage targets:
- All 20 individual check methods
- _approx_eq edge cases (both zero, large values, negative)
- run_all_checks integration: valid payload → pass, broken payload → errors/warnings
- ConsistencyReport status logic (pass, warnings, critical_errors)
- SEBI face value denomination validation
"""

import pytest
from app.ai.consistency_engine import (
    ConsistencyEngine,
    run_consistency_checks,
    _approx_eq,
)
from app.schemas.drhp_v2 import (
    DrhpRequestV2,
    ExtendedCompanyProfile,
    ExtendedPromoterDetail,
    ExtendedIssueDetails,
    ExtendedFinancialYear,
    UsageItem,
    LegalProceeding,
)


# ── _approx_eq ────────────────────────────────────────────────────────────────

class TestApproxEq:
    def test_equal_values(self):
        assert _approx_eq(100.0, 100.0) is True

    def test_within_tolerance(self):
        assert _approx_eq(100.0, 100.5) is True  # 0.5% diff, tol=1%

    def test_outside_tolerance(self):
        assert _approx_eq(100.0, 102.0) is False  # 2% diff, tol=1%

    def test_both_zero(self):
        assert _approx_eq(0.0, 0.0) is True

    def test_large_values_close(self):
        assert _approx_eq(1_000_000.0, 1_009_999.0) is True

    def test_large_values_far(self):
        assert _approx_eq(1_000_000.0, 1_020_000.0) is False

    def test_negative_values(self):
        assert _approx_eq(-100.0, -100.5) is True


# ── Individual Check Tests ────────────────────────────────────────────────────

def _make_req_override(**overrides):
    """Helper: creates a valid DrhpRequestV2 with selective overrides."""
    base = DrhpRequestV2(
        company=ExtendedCompanyProfile(
            name="Test Corp Limited",
            cin="U72900MH2020PTC123456",
            pan="AABCT1234A",
            incorporation_date="2020-01-01",
            registered_address="123 Main St, Mumbai, Maharashtra 400001",
            sector="Technology",
            description="A test company for consistency engine unit testing. " * 5,
        ),
        promoters=[
            ExtendedPromoterDetail(name="Alice", designation="MD", holding_pct=55.0),
            ExtendedPromoterDetail(name="Bob", designation="ED", holding_pct=20.0),
        ],
        financials=[
            ExtendedFinancialYear(year="2021-22", revenue=3000.0, net_profit=150.0, total_assets=5000.0, total_equity=2500.0),
            ExtendedFinancialYear(year="2022-23", revenue=4500.0, net_profit=300.0, total_assets=7000.0, total_equity=3500.0),
            ExtendedFinancialYear(year="2023-24", revenue=6000.0, net_profit=500.0, total_assets=9000.0, total_equity=5000.0),
        ],
        issue=ExtendedIssueDetails(
            issue_size_cr=18.0,
            fresh_issue_cr=12.0,
            ofs_cr=6.0,
            price_band_low=120.0,
            price_band_high=128.0,
            face_value=10.0,
            lot_size=1000,
            objects_of_issue="1. Infrastructure expansion ₹6Cr\n2. Working capital ₹4Cr\n3. Corporate purposes ₹2Cr",
            merchant_banker="Axis Capital Limited",
        ),
        **overrides,
    )
    return base


class TestCheckCompanyName:
    def test_valid_company_name_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_company_name_provided()
        assert engine.passed_checks == 1

    def test_empty_company_name_warns(self):
        req = _make_req_override()
        req.company.name = "X"  # too short
        engine = ConsistencyEngine(req)
        engine._check_company_name_provided()
        assert len(engine.warnings) > 0 or len(engine.errors) > 0


class TestCheckPromoterHoldings:
    def test_valid_holdings_pass(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_promoter_holdings_sum()
        assert len(engine.errors) == 0

    def test_holdings_exceeding_100_causes_error(self):
        req = _make_req_override()
        req.promoters = [
            ExtendedPromoterDetail(name="Alice", designation="MD", holding_pct=70.0),
            ExtendedPromoterDetail(name="Bob",   designation="ED", holding_pct=35.0),
        ]
        engine = ConsistencyEngine(req)
        engine._check_promoter_holdings_sum()
        assert len(engine.errors) == 1
        assert "PROMOTER_HOLDINGS_SUM" in engine.errors[0].check_name

    def test_no_promoters_warns(self):
        req = _make_req_override()
        req.promoters = []
        engine = ConsistencyEngine(req)
        engine._check_promoter_holdings_sum()
        assert len(engine.warnings) > 0

    def test_low_promoter_holding_warns(self):
        req = _make_req_override()
        req.promoters = [
            ExtendedPromoterDetail(name="Alice", designation="MD", holding_pct=30.0),
        ]
        engine = ConsistencyEngine(req)
        engine._check_promoter_holdings_sum()
        assert any("PROMOTER_MINIMUM" in w.check_name for w in engine.warnings)


class TestCheckIssueStructure:
    def test_valid_issue_structure_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_issue_structure()
        assert len(engine.errors) == 0

    def test_mismatch_causes_error(self):
        req = _make_req_override()
        req.issue.fresh_issue_cr = 10.0
        req.issue.ofs_cr = 5.0
        req.issue.issue_size_cr = 20.0  # Declared ≠ 10+5=15
        engine = ConsistencyEngine(req)
        engine._check_issue_structure()
        assert len(engine.errors) == 1
        assert "ISSUE_STRUCTURE" in engine.errors[0].check_name


class TestCheckFinancialYearSequence:
    def test_ascending_years_pass(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_financial_year_sequence()
        assert len(engine.errors) == 0

    def test_out_of_order_years_cause_error(self):
        req = _make_req_override()
        # Swap last two years
        req.financials[1], req.financials[2] = req.financials[2], req.financials[1]
        engine = ConsistencyEngine(req)
        engine._check_financial_year_sequence()
        assert len(engine.errors) == 1
        assert "SEQUENCE" in engine.errors[0].check_name


class TestCheckBalanceSheet:
    def test_balanced_balance_sheet_passes(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=500.0,
                total_assets=9000.0, total_equity=5000.0,
                total_liabilities=4000.0,  # 9000 - 5000 = 4000 ✓
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_balance_sheet_equation()
        assert len(engine.warnings) == 0

    def test_imbalanced_balance_sheet_warns(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=500.0,
                total_assets=9000.0, total_equity=5000.0,
                total_liabilities=3000.0,  # 9000 - 5000 = 4000 ≠ 3000 ✗
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_balance_sheet_equation()
        assert len(engine.warnings) > 0


class TestCheckEbitdaConsistency:
    def test_consistent_ebitda_passes(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=500.0,
                total_assets=9000.0, total_equity=5000.0,
                ebit=800.0, depreciation=200.0, ebitda=1000.0,  # 800+200=1000 ✓
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_ebitda_consistency()
        assert len(engine.warnings) == 0

    def test_inconsistent_ebitda_warns(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=500.0,
                total_assets=9000.0, total_equity=5000.0,
                ebit=800.0, depreciation=200.0, ebitda=800.0,  # 800+200=1000 ≠ 800 ✗
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_ebitda_consistency()
        assert len(engine.warnings) > 0


class TestCheckPatPbtTax:
    def test_consistent_pat_passes(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=600.0,
                total_assets=9000.0, total_equity=5000.0,
                pbt=800.0, tax_expense=200.0,  # 800-200=600 ✓
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_pat_pbt_tax()
        assert len(engine.warnings) == 0

    def test_inconsistent_pat_warns(self):
        req = _make_req_override()
        req.financials = [
            ExtendedFinancialYear(
                year="2023-24", revenue=6000.0, net_profit=500.0,
                total_assets=9000.0, total_equity=5000.0,
                pbt=800.0, tax_expense=200.0,  # 800-200=600 ≠ 500 ✗
            )
        ]
        engine = ConsistencyEngine(req)
        engine._check_pat_pbt_tax()
        assert len(engine.warnings) > 0


class TestCheckPriceBand:
    def test_valid_price_band_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_price_band()
        assert len(engine.errors) == 0

    def test_floor_above_cap_causes_error(self):
        req = _make_req_override()
        req.issue.price_band_low = 200.0
        req.issue.price_band_high = 150.0
        engine = ConsistencyEngine(req)
        engine._check_price_band()
        assert len(engine.errors) == 1
        assert "PRICE_BAND" in engine.errors[0].check_name


class TestCheckFaceValue:
    def test_standard_face_values_pass(self):
        for fv in [1.0, 2.0, 5.0, 10.0]:
            req = _make_req_override()
            req.issue.face_value = fv
            engine = ConsistencyEngine(req)
            engine._check_face_value()
            assert len(engine.errors) == 0, f"face_value={fv} should be valid"

    def test_non_standard_face_value_causes_error(self):
        req = _make_req_override()
        req.issue.face_value = 7.0  # Not a SEBI-approved denomination
        engine = ConsistencyEngine(req)
        engine._check_face_value()
        assert len(engine.errors) > 0 or len(engine.warnings) > 0


class TestCheckCinFormat:
    def test_valid_cin_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_cin_format()
        assert len(engine.errors) == 0

    def test_invalid_cin_causes_error(self):
        req = _make_req_override()
        req.company.cin = "INVALID_CIN_FORMAT"
        engine = ConsistencyEngine(req)
        engine._check_cin_format()
        assert len(engine.errors) > 0 or len(engine.warnings) > 0


class TestCheckMerchantBanker:
    def test_valid_merchant_banker_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_merchant_banker()
        assert len(engine.warnings) == 0

    def test_missing_merchant_banker_warns(self):
        req = _make_req_override()
        req.issue.merchant_banker = ""
        engine = ConsistencyEngine(req)
        engine._check_merchant_banker()
        assert len(engine.warnings) > 0 or len(engine.errors) > 0


class TestCheckObjectsOfIssue:
    def test_valid_objects_of_issue_passes(self, valid_drhp_request):
        engine = ConsistencyEngine(valid_drhp_request)
        engine._check_objects_of_issue()
        assert len(engine.warnings) == 0

    def test_short_objects_warns(self):
        req = _make_req_override()
        req.issue.objects_of_issue = "Short text."
        engine = ConsistencyEngine(req)
        engine._check_objects_of_issue()
        assert len(engine.warnings) > 0 or len(engine.errors) > 0


# ── Full run_all_checks integration ──────────────────────────────────────────

class TestRunAllChecks:
    def test_valid_request_returns_pass_or_warnings(self, valid_drhp_request):
        report = run_consistency_checks(valid_drhp_request)
        assert report.status in ("pass", "warnings")
        assert report.can_generate_pdf is True

    def test_critical_errors_block_pdf(self):
        req = _make_req_override()
        # Create a critical error: floor > cap
        req.issue.price_band_low = 200.0
        req.issue.price_band_high = 100.0
        report = run_consistency_checks(req)
        assert report.can_generate_pdf is False
        assert len(report.errors) > 0

    def test_report_has_correct_check_count(self, valid_drhp_request):
        report = run_consistency_checks(valid_drhp_request)
        assert report.total_checks == 22
        assert report.passed_checks <= 22

    def test_report_errors_are_consistency_flags(self, valid_drhp_request):
        from app.schemas.drhp_v2 import ConsistencyFlag
        report = run_consistency_checks(valid_drhp_request)
        for flag in report.errors + report.warnings + report.info:
            assert isinstance(flag, ConsistencyFlag)
            assert flag.severity in ("critical", "warning", "info")
            assert len(flag.description) > 10

    def test_promoter_and_issue_errors_accumulated(self):
        req = _make_req_override()
        # Multiple errors at once
        req.promoters = [
            ExtendedPromoterDetail(name="A", designation="MD", holding_pct=70.0),
            ExtendedPromoterDetail(name="B", designation="ED", holding_pct=40.0),
        ]
        req.issue.fresh_issue_cr = 5.0
        req.issue.ofs_cr = 5.0
        req.issue.issue_size_cr = 20.0
        report = run_consistency_checks(req)
        assert len(report.errors) >= 2

    def test_legal_proceedings_material_amount_warns(self):
        from app.schemas.drhp_v2 import LegalProceeding
        req = _make_req_override()
        req.legal_proceedings = [
            LegalProceeding(
                court_or_tribunal="High Court Mumbai",
                nature_of_case="Contract Dispute",
                amount_involved_lakhs=50000.0,  # >10000 → material warning
                current_status="Pending",
            )
        ]
        report = run_consistency_checks(req)
        assert any("LEGAL" in w.check_name for w in report.warnings)
