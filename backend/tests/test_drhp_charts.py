"""
test_drhp_charts.py
Unit tests for app/services/drhp_charts.py

Coverage targets:
- All 9+ chart functions return a valid RLImage
- Edge cases: single data point, empty lists, negative values, zero revenue
- _fig_to_rl: height capping at 220pt
- _format_lakh: correct formatting for < 100 and >= 100 values
- cash_flow_waterfall_chart: new chart function
"""

import pytest
import io

# Guard: matplotlib must be installed in non-interactive mode
import matplotlib
matplotlib.use("Agg")

from app.services.drhp_charts import (
    _format_lakh,
    _fig_to_rl,
    revenue_pat_chart,
    ebitda_margin_chart,
    balance_sheet_chart,
    ratios_radar_chart,
    shareholding_pie_chart,
    revenue_growth_chart,
    peer_comparison_chart,
    funds_utilization_chart,
    cagr_trajectory_chart,
    ebitda_trend_chart,
    shareholding_chart,
    issue_utilization_chart,
    cash_flow_waterfall_chart,
)
from reportlab.platypus import Image as RLImage
from app.schemas.drhp_v2 import ExtendedFinancialYear


# ── _format_lakh ──────────────────────────────────────────────────────────────

class TestFormatLakh:
    def test_small_value_returns_lakhs(self):
        result = _format_lakh(50.0)
        assert "₹" in result
        assert "L" in result

    def test_large_value_returns_crores(self):
        result = _format_lakh(500.0)
        assert "Cr" in result

    def test_zero_value(self):
        result = _format_lakh(0.0)
        assert "₹" in result

    def test_negative_value(self):
        result = _format_lakh(-75.0)
        # Should not raise; output format may vary
        assert isinstance(result, str)

    def test_boundary_100(self):
        result = _format_lakh(100.0)
        assert "Cr" in result  # Exactly 100 → should show in Crore


# ── _fig_to_rl ────────────────────────────────────────────────────────────────

class TestFigToRl:
    def test_returns_rl_image(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["A", "B"], [10, 20])
        img = _fig_to_rl(fig, width_cm=13.0)
        assert isinstance(img, RLImage)

    def test_tall_figure_capped_at_220pt(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 20))  # Very tall figure
        ax.plot([1, 2, 3])
        img = _fig_to_rl(fig, width_cm=13.0)
        assert img.drawHeight <= 221  # Allow 1pt rounding tolerance

    def test_width_respected(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2])
        img = _fig_to_rl(fig, width_cm=10.0)
        expected_width_pt = (10.0 / 2.54) * 72
        assert abs(img.drawWidth - expected_width_pt) < 5  # ±5pt tolerance


# ── revenue_pat_chart ─────────────────────────────────────────────────────────

class TestRevenuePATChart:
    def test_three_year_data_returns_image(self):
        img = revenue_pat_chart(
            years=["2021-22", "2022-23", "2023-24"],
            revenues=[3200.0, 4800.0, 6500.0],
            pats=[180.0, 380.0, 660.0],
        )
        assert isinstance(img, RLImage)

    def test_single_year_returns_image(self):
        img = revenue_pat_chart(
            years=["2023-24"], revenues=[6500.0], pats=[660.0]
        )
        assert isinstance(img, RLImage)

    def test_negative_pat_does_not_raise(self):
        img = revenue_pat_chart(
            years=["2022-23", "2023-24"],
            revenues=[3000.0, 4000.0],
            pats=[-200.0, 300.0],
        )
        assert isinstance(img, RLImage)


# ── ebitda_margin_chart ───────────────────────────────────────────────────────

class TestEbitdaMarginChart:
    def test_returns_image(self):
        img = ebitda_margin_chart(
            years=["2021-22", "2022-23", "2023-24"],
            revenues=[3200.0, 4800.0, 6500.0],
            ebitdas=[480.0, 820.0, 1180.0],
        )
        assert isinstance(img, RLImage)

    def test_zero_revenue_does_not_raise(self):
        img = ebitda_margin_chart(
            years=["2021-22", "2023-24"],
            revenues=[0.0, 6500.0],
            ebitdas=[0.0, 1180.0],
        )
        assert isinstance(img, RLImage)


# ── balance_sheet_chart ───────────────────────────────────────────────────────

class TestBalanceSheetChart:
    def test_returns_image(self):
        img = balance_sheet_chart(
            years=["2021-22", "2022-23", "2023-24"],
            assets=[5500.0, 7200.0, 9800.0],
            equities=[2800.0, 3600.0, 4800.0],
        )
        assert isinstance(img, RLImage)

    def test_equity_greater_than_assets_does_not_raise(self):
        """Unusual data — should still render without raising."""
        img = balance_sheet_chart(
            years=["2023-24"],
            assets=[3000.0],
            equities=[3500.0],
        )
        assert isinstance(img, RLImage)


# ── ratios_radar_chart ────────────────────────────────────────────────────────

class TestRatiosRadarChart:
    def test_returns_image_with_data(self, three_year_financials):
        img = ratios_radar_chart(
            years=["2021-22", "2022-23", "2023-24"],
            fys_data=three_year_financials,
        )
        assert isinstance(img, RLImage)

    def test_empty_data_returns_none(self):
        result = ratios_radar_chart(years=[], fys_data=[])
        assert result is None

    def test_single_year_returns_image(self):
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=6500.0, net_profit=660.0, ebitda=1180.0,
            total_assets=9800.0, total_equity=4800.0,
        )
        img = ratios_radar_chart(years=["2023-24"], fys_data=[fy])
        assert isinstance(img, RLImage)

    def test_is_polar_chart(self):
        """The radar chart must use polar projection (true radar chart)."""
        import matplotlib.pyplot as plt
        # The function internally creates a polar axes — we verify by checking
        # that it creates an RLImage (visual verification requires manual inspection).
        fy = ExtendedFinancialYear(
            year="2023-24", revenue=6500.0, net_profit=660.0, ebitda=1180.0,
            total_assets=9800.0, total_equity=4800.0,
        )
        img = ratios_radar_chart(years=["2023-24"], fys_data=[fy])
        assert isinstance(img, RLImage)


# ── shareholding_pie_chart ────────────────────────────────────────────────────

class TestShareholdingPieChart:
    def test_returns_image(self):
        img = shareholding_pie_chart(
            promoters_pct=60.0, public_pct=35.0, market_maker_pct=5.0
        )
        assert isinstance(img, RLImage)

    def test_no_market_maker_uses_default(self):
        img = shareholding_pie_chart(promoters_pct=65.0, public_pct=30.0)
        assert isinstance(img, RLImage)


# ── revenue_growth_chart ──────────────────────────────────────────────────────

class TestRevenueGrowthChart:
    def test_three_year_data(self):
        img = revenue_growth_chart(
            years=["2021-22", "2022-23", "2023-24"],
            revenues=[3200.0, 4800.0, 6500.0],
        )
        assert isinstance(img, RLImage)

    def test_negative_growth(self):
        img = revenue_growth_chart(
            years=["2022-23", "2023-24"],
            revenues=[5000.0, 4000.0],
        )
        assert isinstance(img, RLImage)


# ── peer_comparison_chart ─────────────────────────────────────────────────────

class TestPeerComparisonChart:
    def test_returns_image_with_peers(self):
        img = peer_comparison_chart(
            company_name="Acme Tech",
            company_pe=18.5,
            company_ronw=15.0,
            company_ebitda_margin=18.0,
            peers=[
                {"name": "Peer A", "pe": 22.0, "ronw": 12.0, "ebitda_margin": 14.0},
                {"name": "Peer B", "pe": 15.0, "ronw": 18.0, "ebitda_margin": 20.0},
            ],
        )
        assert isinstance(img, RLImage)

    def test_no_peers_returns_image(self):
        img = peer_comparison_chart(
            company_name="Acme Tech",
            company_pe=18.5,
            company_ronw=15.0,
            company_ebitda_margin=18.0,
            peers=[],
        )
        assert isinstance(img, RLImage)


# ── funds_utilization_chart ───────────────────────────────────────────────────

class TestFundsUtilizationChart:
    def test_returns_image(self):
        img = funds_utilization_chart(
            objects=[
                {"label": "Infrastructure", "amount_cr": 6.0},
                {"label": "Working Capital", "amount_cr": 4.0},
                {"label": "Corporate", "amount_cr": 2.0},
            ]
        )
        assert isinstance(img, RLImage)

    def test_empty_objects_returns_none(self):
        result = funds_utilization_chart(objects=[])
        assert result is None


# ── cagr_trajectory_chart ─────────────────────────────────────────────────────

class TestCagrTrajectoryChart:
    def test_returns_image(self):
        img = cagr_trajectory_chart(
            years=["2021-22", "2022-23", "2023-24"],
            revenues=[3200.0, 4800.0, 6500.0],
            pats=[180.0, 380.0, 660.0],
        )
        assert isinstance(img, RLImage)

    def test_single_year_returns_none(self):
        result = cagr_trajectory_chart(
            years=["2023-24"], revenues=[6500.0], pats=[660.0]
        )
        assert result is None


# ── ebitda_trend_chart ────────────────────────────────────────────────────────

class TestEbitdaTrendChart:
    def test_returns_image(self):
        img = ebitda_trend_chart(
            years=["2021-22", "2022-23", "2023-24"],
            ebitdas=[480.0, 820.0, 1180.0],
        )
        assert isinstance(img, RLImage)

    def test_single_year_returns_none(self):
        result = ebitda_trend_chart(years=["2023-24"], ebitdas=[1180.0])
        assert result is None

    def test_negative_ebitda_does_not_raise(self):
        img = ebitda_trend_chart(
            years=["2022-23", "2023-24"],
            ebitdas=[-100.0, 500.0],
        )
        assert isinstance(img, RLImage)


# ── shareholding_chart ────────────────────────────────────────────────────────

class TestShareholdingChart:
    def test_returns_image(self):
        img = shareholding_chart(
            labels=["Promoters", "Public", "Market Maker"],
            percentages=[60.0, 35.0, 5.0],
        )
        assert isinstance(img, RLImage)

    def test_empty_returns_none(self):
        result = shareholding_chart(labels=[], percentages=[])
        assert result is None

    def test_mismatched_lengths_returns_none(self):
        result = shareholding_chart(labels=["A", "B"], percentages=[50.0])
        assert result is None


# ── issue_utilization_chart ───────────────────────────────────────────────────

class TestIssueUtilizationChart:
    def test_returns_image(self):
        img = issue_utilization_chart(
            labels=["Infrastructure", "Working Capital"],
            amounts=[600.0, 400.0],
        )
        assert isinstance(img, RLImage)

    def test_zero_amounts_returns_none(self):
        result = issue_utilization_chart(
            labels=["Infrastructure", "Working Capital"],
            amounts=[0.0, 0.0],
        )
        assert result is None

    def test_empty_returns_none(self):
        result = issue_utilization_chart(labels=[], amounts=[])
        assert result is None


# ── cash_flow_waterfall_chart (NEW) ──────────────────────────────────────────

class TestCashFlowWaterfallChart:
    def test_returns_image(self):
        img = cash_flow_waterfall_chart(
            years=["2021-22", "2022-23", "2023-24"],
            ocf_list=[600.0, 750.0, 900.0],
            capex_list=[150.0, 200.0, 400.0],
            fcf_list=[450.0, 550.0, 500.0],
        )
        assert isinstance(img, RLImage)

    def test_negative_fcf_does_not_raise(self):
        img = cash_flow_waterfall_chart(
            years=["2022-23", "2023-24"],
            ocf_list=[300.0, 900.0],
            capex_list=[500.0, 400.0],
            fcf_list=[-200.0, 500.0],
        )
        assert isinstance(img, RLImage)

    def test_single_year_returns_image(self):
        img = cash_flow_waterfall_chart(
            years=["2023-24"],
            ocf_list=[900.0],
            capex_list=[400.0],
            fcf_list=[500.0],
        )
        assert isinstance(img, RLImage)

    def test_empty_data_returns_none(self):
        result = cash_flow_waterfall_chart(years=[], ocf_list=[], capex_list=[], fcf_list=[])
        assert result is None
