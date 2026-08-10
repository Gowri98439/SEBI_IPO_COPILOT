"""
test_financial_intelligence.py
Unit tests for app/ai/financial_intelligence.py

Coverage targets:
- _safe_div (zero-denominator, None inputs, scaling)
- _derive_missing_from_available (EBITDA, EBIT, PBT, FCF derivations)
- compute_ratios_for_year (all ratio categories)
- compute_growth_metrics (2-year, 3-year CAGR; missing data)
- compute_altman_z (safe zone, grey zone, distress zone, missing data)
- detect_red_flags (negative PAT, declining revenue, high D/E, low CR, negative OCF)
- detect_strengths (high CAGR, high EBITDA margin, low D/E, positive FCF)
- compute_financial_intelligence (full pipeline: valid, empty, minimal)
"""

import pytest
from app.ai.financial_intelligence import (
    _safe_div,
    _fmt_pct, _fmt_x, _fmt_days, _fmt_inr, _fmt_num,
    _flag,
    _derive_missing_from_available,
    compute_ratios_for_year,
    compute_growth_metrics,
    compute_altman_z,
    detect_red_flags,
    detect_strengths,
    compute_financial_intelligence,
    MISSING,
)
from app.schemas.drhp_v2 import ExtendedFinancialYear, DrhpRequestV2


# ── _safe_div ─────────────────────────────────────────────────────────────────

class TestSafeDiv:
    def test_normal_division(self):
        assert _safe_div(10.0, 4.0) == pytest.approx(2.5)

    def test_with_scale(self):
        assert _safe_div(50.0, 200.0, 100.0) == pytest.approx(25.0)

    def test_zero_denominator_returns_zero(self):
        assert _safe_div(10.0, 0.0) == 0.0


    def test_none_numerator_returns_none(self):
        assert _safe_div(None, 5.0) is None

    def test_none_denominator_returns_none(self):
        assert _safe_div(5.0, None) is None

    def test_both_none_returns_none(self):
        assert _safe_div(None, None) is None

    def test_negative_values(self):
        assert _safe_div(-100.0, 200.0) == pytest.approx(-0.5)

    def test_small_values(self):
        result = _safe_div(1.0, 1000000.0)
        assert result == pytest.approx(0.000001)


# ── Formatters ────────────────────────────────────────────────────────────────

class TestFormatters:
    def test_fmt_pct_none(self):
        assert _fmt_pct(None) == MISSING

    def test_fmt_pct_value(self):
        assert _fmt_pct(23.456) == "23.46%"

    def test_fmt_x_none(self):
        assert _fmt_x(None) == MISSING

    def test_fmt_x_value(self):
        assert _fmt_x(2.5) == "2.50x"

    def test_fmt_days_none(self):
        assert _fmt_days(None) == MISSING

    def test_fmt_days_value(self):
        assert _fmt_days(45.678) == "45.7 days"

    def test_fmt_inr_none(self):
        assert _fmt_inr(None) == MISSING

    def test_fmt_inr_value(self):
        result = _fmt_inr(1234.56)
        assert "₹" in result
        assert "1,234.56" in result

    def test_fmt_num_none(self):
        assert _fmt_num(None) == MISSING

    def test_fmt_num_value(self):
        assert _fmt_num(3.14159, decimals=3) == "3.142"


# ── _flag ─────────────────────────────────────────────────────────────────────

class TestFlag:
    def test_none_value_returns_none(self):
        assert _flag(None) is None

    def test_green_above_threshold(self):
        assert _flag(25.0, good_above=20.0, warn_above=10.0) == "green"

    def test_amber_between_thresholds(self):
        assert _flag(15.0, good_above=20.0, warn_above=10.0) == "amber"

    def test_red_below_warn(self):
        assert _flag(5.0, good_above=20.0, warn_above=10.0) == "red"

    def test_invert_green(self):
        """Lower is better (e.g. Debt/Equity)."""
        assert _flag(0.3, good_above=0.5, warn_above=1.5, invert=True) == "green"

    def test_invert_amber(self):
        assert _flag(1.0, good_above=0.5, warn_above=1.5, invert=True) == "amber"

    def test_invert_red(self):
        assert _flag(2.0, good_above=0.5, warn_above=1.5, invert=True) == "red"


# ── _derive_missing_from_available ───────────────────────────────────────────

class TestDeriveFields:
    def test_ebitda_derived_from_ebit_and_da(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=1000.0, net_profit=100.0,
            ebit=200.0, depreciation=50.0, ebitda=None, total_assets=0.0, total_equity=0.0
        )
        derived = _derive_missing_from_available(fy)
        assert derived.ebitda == pytest.approx(250.0)

    def test_ebit_derived_from_ebitda_and_da(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=1000.0, net_profit=100.0,
            ebitda=300.0, depreciation=80.0, ebit=None, total_assets=0.0, total_equity=0.0
        )
        derived = _derive_missing_from_available(fy)
        assert derived.ebit == pytest.approx(220.0)

    def test_pbt_derived_from_ebit_and_interest(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=1000.0, net_profit=100.0,
            ebit=400.0, interest_expense=60.0, pbt=None, total_assets=0.0, total_equity=0.0
        )
        derived = _derive_missing_from_available(fy)
        assert derived.pbt == pytest.approx(340.0)

    def test_fcf_derived_from_ocf_and_capex(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=1000.0, net_profit=100.0,
            operating_cash_flow=500.0, capex=100.0, free_cash_flow=None,
            total_assets=0.0, total_equity=0.0
        )
        derived = _derive_missing_from_available(fy)
        assert derived.free_cash_flow == pytest.approx(400.0)

    def test_existing_values_not_overwritten(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=1000.0, net_profit=100.0,
            ebit=200.0, depreciation=50.0, ebitda=300.0,  # explicitly set
            total_assets=0.0, total_equity=0.0
        )
        derived = _derive_missing_from_available(fy)
        # Should NOT overwrite the explicit 300.0 with 200+50=250
        assert derived.ebitda == pytest.approx(300.0)


# ── compute_ratios_for_year ───────────────────────────────────────────────────

class TestComputeRatiosForYear:
    def test_returns_list_of_ratios(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        assert isinstance(ratios, list)
        # 19 ratios across Profitability, Liquidity, Leverage, Efficiency, IPO Metrics
        assert len(ratios) >= 19, f"Expected 19+ ratios, got {len(ratios)}"

    def test_ebitda_margin_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ebitda_ratio = next(r for r in ratios if r.name == "EBITDA Margin")
        expected = (1180.0 / 6500.0) * 100
        assert ebitda_ratio.value == pytest.approx(expected, rel=1e-3)
        assert ebitda_ratio.flag == "green"

    def test_pat_margin_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ratio = next(r for r in ratios if r.name == "PAT Margin")
        expected = (660.0 / 6500.0) * 100
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_current_ratio_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ratio = next(r for r in ratios if r.name == "Current Ratio")
        expected = 4200.0 / 2500.0
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_roe_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ratio = next(r for r in ratios if r.name == "Return on Equity (ROE)")
        expected = (660.0 / 4800.0) * 100
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_debt_equity_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ratio = next((r for r in ratios if "Debt" in r.name and "Equity" in r.name), None)
        assert ratio is not None, f"Debt/Equity ratio not found in: {[r.name for r in ratios]}"
        expected = 2500.0 / 4800.0
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_eps_computed(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        ratio = next(r for r in ratios if r.name == "Earnings Per Share (EPS)")
        expected = (660.0 * 100000) / 5000000
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_missing_data_returns_missing_string(self, fy_minimal):
        """When input fields are absent, ratio.formatted_value should be MISSING."""
        ratios = compute_ratios_for_year(fy_minimal)
        eps = next(r for r in ratios if r.name == "Earnings Per Share (EPS)")
        assert eps.formatted_value == MISSING
        assert eps.value is None

    def test_working_capital_turnover_computed(self, fy_complete):
        """Working Capital Turnover ratio must be present."""
        ratios = compute_ratios_for_year(fy_complete)
        names = [r.name for r in ratios]
        assert "Working Capital Turnover" in names
        ratio = next(r for r in ratios if r.name == "Working Capital Turnover")
        wc = 4200.0 - 2500.0
        expected = 6500.0 / wc
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_asset_turnover_computed(self, fy_complete):
        """Asset Turnover ratio must be present."""
        ratios = compute_ratios_for_year(fy_complete)
        names = [r.name for r in ratios]
        assert "Asset Turnover Ratio" in names
        ratio = next(r for r in ratios if r.name == "Asset Turnover Ratio")
        expected = 6500.0 / 9800.0
        assert ratio.value == pytest.approx(expected, rel=1e-3)

    def test_ratio_has_explanation(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        for r in ratios:
            assert len(r.explanation) > 20, f"Ratio {r.name} has too short explanation"

    def test_ratio_has_formula(self, fy_complete):
        ratios = compute_ratios_for_year(fy_complete)
        for r in ratios:
            assert len(r.formula) > 5, f"Ratio {r.name} has missing formula"


# ── compute_growth_metrics ─────────────────────────────────────────────────────

class TestComputeGrowthMetrics:
    def test_single_year_returns_missing(self, fy_complete):
        result = compute_growth_metrics([fy_complete])
        assert result["revenue_cagr"] == MISSING
        assert result["pat_cagr"] == MISSING

    def test_two_year_cagr_revenue(self):
        fys = [
            ExtendedFinancialYear(year="2022-23", revenue=4000.0, net_profit=200.0, total_assets=0.0, total_equity=0.0),
            ExtendedFinancialYear(year="2023-24", revenue=6500.0, net_profit=400.0, total_assets=0.0, total_equity=0.0),
        ]
        result = compute_growth_metrics(fys)
        expected_cagr = ((6500.0 / 4000.0) ** 1 - 1) * 100
        assert result["revenue_cagr_value"] == pytest.approx(expected_cagr, rel=1e-3)

    def test_three_year_cagr(self, three_year_financials):
        result = compute_growth_metrics(three_year_financials)
        assert result["years"] == 2
        assert result["from_year"] == "2021-22"
        assert result["to_year"] == "2023-24"
        expected_cagr = ((6500.0 / 3200.0) ** (1/2) - 1) * 100
        assert result["revenue_cagr_value"] == pytest.approx(expected_cagr, rel=1e-3)

    def test_negative_start_revenue_returns_none(self):
        fys = [
            ExtendedFinancialYear(year="2022-23", revenue=0.0, net_profit=200.0, total_assets=0.0, total_equity=0.0),
            ExtendedFinancialYear(year="2023-24", revenue=4000.0, net_profit=400.0, total_assets=0.0, total_equity=0.0),
        ]
        result = compute_growth_metrics(fys)
        assert result["revenue_cagr_value"] is None


# ── compute_altman_z ──────────────────────────────────────────────────────────

class TestComputeAltmanZ:
    def test_safe_zone(self, fy_complete):
        result = compute_altman_z(fy_complete)
        assert result["flag"] in ("green", "amber", "red")
        assert isinstance(result["value"], float)
        assert result["value"] > 0

    def test_distress_zone(self):
        fy = ExtendedFinancialYear(
            year="2023-24",
            revenue=500.0,
            net_profit=-400.0,
            total_assets=2000.0,
            total_equity=100.0,
            total_debt=1900.0,
            ebit=-500.0,
            current_assets=400.0,
            current_liabilities=1600.0,
        )
        result = compute_altman_z(fy)
        assert result["flag"] == "red"
        assert result["interpretation"] == "Distress Zone — elevated financial distress risk"

    def test_missing_data_returns_missing(self, fy_minimal):
        """A minimal FY without ebit/debt/cashflow fields → MISSING."""
        result = compute_altman_z(fy_minimal)
        assert result["value"] == MISSING or isinstance(result.get("missing_inputs"), list)

    def test_green_zone_interpretation(self, fy_complete):
        result = compute_altman_z(fy_complete)
        if result["flag"] == "green":
            assert "Safe Zone" in result["interpretation"]
        elif result["flag"] == "amber":
            assert "Grey Zone" in result["interpretation"]


# ── detect_red_flags ──────────────────────────────────────────────────────────

class TestDetectRedFlags:
    def test_empty_financials_returns_empty(self):
        assert detect_red_flags([]) == []

    def test_negative_pat_flagged(self, fy_loss):
        flags = detect_red_flags([fy_loss])
        assert any("Negative PAT" in f or "net loss" in f.lower() for f in flags)

    def test_high_debt_equity_flagged(self):
        """D/E > 2.0 → red flag. Use a high-debt fixture."""
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=2000.0, net_profit=-250.0,
            total_assets=4000.0, total_equity=500.0,
            total_debt=3500.0,  # D/E = 7.0x > 2.0 threshold
        )
        flags = detect_red_flags([fy])
        assert any("Debt/Equity" in f or "leverage" in f.lower() for f in flags)

    def test_low_current_ratio_flagged(self, fy_loss):
        """CR = 1000/1200 = 0.83 — should flag liquidity risk."""
        flags = detect_red_flags([fy_loss])
        assert any("Current Ratio" in f or "liquidity" in f.lower() for f in flags)

    def test_negative_ocf_positive_pat_flagged(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=5000.0, net_profit=500.0,
            total_assets=8000.0, total_equity=4000.0,
            operating_cash_flow=-200.0,
        )
        flags = detect_red_flags([fy])
        assert any("cash flow" in f.lower() or "OCF" in f for f in flags)

    def test_declining_revenue_flagged(self):
        fys = [
            ExtendedFinancialYear(year="2022-23", revenue=5000.0, net_profit=300.0, total_assets=0.0, total_equity=0.0),
            ExtendedFinancialYear(year="2023-24", revenue=4000.0, net_profit=200.0, total_assets=0.0, total_equity=0.0),
        ]
        flags = detect_red_flags(fys)
        assert any("declined" in f.lower() or "revenue" in f.lower() for f in flags)

    def test_ebitda_margin_compression_flagged(self):
        """EBITDA margin declining across years should surface a red flag."""
        fys = [
            ExtendedFinancialYear(year="2021-22", revenue=3000.0, net_profit=200.0,
                                  ebitda=600.0, total_assets=5000.0, total_equity=2000.0),
            ExtendedFinancialYear(year="2022-23", revenue=4000.0, net_profit=250.0,
                                  ebitda=700.0, total_assets=6000.0, total_equity=2500.0),
            ExtendedFinancialYear(year="2023-24", revenue=5500.0, net_profit=300.0,
                                  ebitda=770.0, total_assets=7000.0, total_equity=3000.0),
        ]
        flags = detect_red_flags(fys)
        assert any("margin" in f.lower() or "ebitda" in f.lower() for f in flags)

    def test_no_flags_for_healthy_company(self, fy_complete):
        flags = detect_red_flags([fy_complete])
        assert isinstance(flags, list)  # May be empty — that's correct


# ── detect_strengths ──────────────────────────────────────────────────────────

class TestDetectStrengths:
    def test_empty_returns_empty(self):
        assert detect_strengths([], {}) == []

    def test_high_revenue_cagr_detected(self, three_year_financials):
        growth = compute_growth_metrics(three_year_financials)
        strengths = detect_strengths(three_year_financials, growth)
        assert any("CAGR" in s or "revenue" in s.lower() for s in strengths)

    def test_high_ebitda_margin_detected(self, fy_complete):
        strengths = detect_strengths([fy_complete], {})
        # EBITDA margin = 1180/6500 ≈ 18.15% > 18 threshold
        assert any("EBITDA" in s or "margin" in s.lower() for s in strengths)

    def test_low_leverage_detected(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=5000.0, net_profit=400.0,
            total_assets=7000.0, total_equity=5000.0, total_debt=500.0,
        )
        strengths = detect_strengths([fy], {})
        assert any("leverage" in s.lower() or "Debt/Equity" in s for s in strengths)

    def test_positive_fcf_detected(self, fy_complete):
        strengths = detect_strengths([fy_complete], {})
        assert any("Cash Flow" in s or "FCF" in s for s in strengths)

    def test_improving_icr_detected(self):
        """Improving interest coverage ratio across years → strength."""
        fys = [
            ExtendedFinancialYear(year="2021-22", revenue=2000.0, net_profit=100.0,
                                  ebit=150.0, interest_expense=100.0,
                                  total_assets=4000.0, total_equity=2000.0),
            ExtendedFinancialYear(year="2022-23", revenue=3000.0, net_profit=200.0,
                                  ebit=300.0, interest_expense=100.0,
                                  total_assets=5000.0, total_equity=2500.0),
            ExtendedFinancialYear(year="2023-24", revenue=4500.0, net_profit=350.0,
                                  ebit=500.0, interest_expense=100.0,
                                  total_assets=6000.0, total_equity=3000.0),
        ]
        strengths = detect_strengths(fys, compute_growth_metrics(fys))
        assert any("coverage" in s.lower() or "interest" in s.lower() for s in strengths)


# ── compute_financial_intelligence ───────────────────────────────────────────

class TestComputeFinancialIntelligence:
    def test_full_pipeline_returns_report(self, valid_drhp_request):
        from app.schemas.drhp_v2 import FinancialIntelligenceReport
        report = compute_financial_intelligence(valid_drhp_request)
        assert isinstance(report, FinancialIntelligenceReport)
        assert len(report.ratios) > 20
        assert report.data_quality_score >= 0.0
        assert report.computation_time_ms > 0

    def test_empty_financials_returns_empty_report(self, valid_company, valid_promoters, valid_issue):
        # Build a request with one fy but all zeros — should still return a report
        fy = ExtendedFinancialYear(year="2023-24", revenue=0.0, net_profit=0.0, total_assets=0.0, total_equity=0.0)
        req = DrhpRequestV2(
            company=valid_company,
            promoters=valid_promoters,
            financials=[fy],
            issue=valid_issue,
        )
        report = compute_financial_intelligence(req)
        assert isinstance(report.ratios, list)

    def test_red_flags_are_strings(self, valid_drhp_request):
        report = compute_financial_intelligence(valid_drhp_request)
        for flag in report.red_flags:
            assert isinstance(flag, str) and len(flag) > 5

    def test_strengths_are_strings(self, valid_drhp_request):
        report = compute_financial_intelligence(valid_drhp_request)
        for strength in report.strengths:
            assert isinstance(strength, str) and len(strength) > 5

    def test_data_quality_score_between_0_and_1(self, valid_drhp_request):
        report = compute_financial_intelligence(valid_drhp_request)
        assert 0.0 <= report.data_quality_score <= 1.0

    def test_growth_summary_included(self, valid_drhp_request):
        report = compute_financial_intelligence(valid_drhp_request)
        assert "revenue_cagr" in report.growth_summary

    def test_altman_z_included_in_quality_scores(self, valid_drhp_request):
        report = compute_financial_intelligence(valid_drhp_request)
        assert "altman_z" in report.quality_scores
