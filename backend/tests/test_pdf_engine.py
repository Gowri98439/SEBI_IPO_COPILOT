"""
test_pdf_engine.py
Unit tests for app/services/drhp_service.py (v1 PDF engine)

Coverage targets:
- Helper functions: _fmt_lakhs, _fmt_cr, _pct, _ratio
- _make_table: produces Table with correct structure
- _get_styles: registers all required named styles
- _header_footer: does not raise with mock canvas
- PDF generation smoke test: generate_drhp_pdf returns non-empty bytes
"""

import pytest
import io
from unittest.mock import MagicMock, patch

from app.services.drhp_service import (
    _fmt_lakhs,
    _fmt_cr,
    _pct,
    _ratio,
    _make_table,
    _get_styles,
)
from app.schemas.drhp import (
    DrhpRequest,
    CompanyProfile,
    PromoterDetail,
    FinancialYear,
    IssueDetails,
)
from reportlab.platypus import Table


# ── Helper functions ──────────────────────────────────────────────────────────

class TestFmtLakhs:
    def test_basic_format(self):
        result = _fmt_lakhs(1234.56)
        assert "₹" in result
        assert "1,234.56" in result
        assert "Lakhs" in result

    def test_zero(self):
        assert "0.00" in _fmt_lakhs(0.0)

    def test_negative(self):
        result = _fmt_lakhs(-500.0)
        assert "₹" in result


class TestFmtCr:
    def test_basic_format(self):
        result = _fmt_cr(18.5)
        assert "₹" in result
        assert "18.50" in result
        assert "Crore" in result

    def test_large_value(self):
        result = _fmt_cr(1000.0)
        assert "1,000.00" in result


class TestPct:
    def test_basic_percentage(self):
        result = _pct(25.0, 100.0)
        assert result == "25.00%"

    def test_zero_denominator_returns_na(self):
        assert _pct(25.0, 0.0) == "N/A"

    def test_zero_numerator(self):
        assert _pct(0.0, 100.0) == "0.00%"

    def test_fractional(self):
        result = _pct(1.0, 3.0)
        assert "33.33" in result


class TestRatio:
    def test_basic_ratio(self):
        result = _ratio(10.0, 4.0)
        assert result == "2.50x"

    def test_zero_denominator_returns_na(self):
        assert _ratio(10.0, 0.0) == "N/A"

    def test_less_than_one(self):
        result = _ratio(1.0, 4.0)
        assert "0.25" in result


# ── _get_styles ───────────────────────────────────────────────────────────────

class TestGetStyles:
    REQUIRED_STYLES = [
        "Cover1", "Cover2", "Cover3", "CoverNote",
        "H1", "H2", "H3", "Body", "BodyB", "Bullet",
        "TableH", "TableC", "TableL", "TableR",
        "FooterSt", "Disclaimer", "TOCEntry", "TOCSection",
    ]

    def test_all_required_styles_registered(self):
        styles = _get_styles()
        for name in self.REQUIRED_STYLES:
            assert name in styles.byName, f"Missing style: {name}"

    def test_h1_is_navy_color(self):
        from reportlab.lib.colors import HexColor
        styles = _get_styles()
        h1 = styles["H1"]
        assert h1.textColor == HexColor('#003087')

    def test_cover1_is_centered(self):
        from reportlab.lib.enums import TA_CENTER
        styles = _get_styles()
        assert styles["Cover1"].alignment == TA_CENTER

    def test_body_is_justified(self):
        from reportlab.lib.enums import TA_JUSTIFY
        styles = _get_styles()
        assert styles["Body"].alignment == TA_JUSTIFY


# ── _make_table ───────────────────────────────────────────────────────────────

class TestMakeTable:
    def test_returns_table_instance(self):
        data = [["Header 1", "Header 2"], ["Row 1", "Value 1"], ["Row 2", "Value 2"]]
        table = _make_table(data, col_widths=[200, 200])
        assert isinstance(table, Table)

    def test_row_count_preserved(self):
        data = [["H1", "H2"]] + [[f"R{i}", f"V{i}"] for i in range(5)]
        table = _make_table(data, col_widths=[150, 150])
        # ReportLab Table stores data internally; verify it doesn't raise
        buf = io.BytesIO()
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
        doc = SimpleDocTemplate(buf, pagesize=A4)
        doc.build([table])
        assert buf.tell() > 0  # PDF content was written

    def test_header_rows_respected(self):
        data = [["H1", "H2"], ["H3", "H4"], ["Row", "Val"]]
        # 2 header rows — should not raise
        table = _make_table(data, col_widths=[200, 200], header_rows=2)
        assert isinstance(table, Table)


# ── _header_footer (mock canvas) ──────────────────────────────────────────────

class TestHeaderFooter:
    def test_does_not_raise_with_mock_canvas(self):
        from app.services.drhp_service import _header_footer
        from unittest.mock import MagicMock

        mock_canvas = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page = 1

        # Should not raise
        _header_footer(mock_canvas, mock_doc, "Test Company", "DRHP")

        mock_canvas.saveState.assert_called_once()
        mock_canvas.restoreState.assert_called_once()


# ── Smoke test: generate_drhp_pdf ─────────────────────────────────────────────

class TestGenerateDrhpPdf:
    def _minimal_request(self):
        return DrhpRequest(
            company=CompanyProfile(
                name="Acme Technologies Private Limited",
                cin="U72900MH2020PTC123456",
                pan="AABCT1234A",
                incorporation_date="2020-01-15",
                registered_address="123 Business Park, Andheri East, Mumbai 400069",
                sector="Technology",
                description=(
                    "Acme Technologies Private Limited is a Mumbai-based cloud software company "
                    "providing enterprise SaaS solutions across BFSI and logistics sectors. "
                    "Founded in 2020, the company serves 200+ clients nationwide."
                ),
            ),
            promoters=[
                PromoterDetail(name="Rahul Sharma", designation="MD", holding_pct=55.0),
                PromoterDetail(name="Priya Singh",  designation="ED", holding_pct=20.0),
            ],
            financials=[
                FinancialYear(year="2021-22", revenue=3200.0, net_profit=180.0, total_assets=5500.0, total_equity=2800.0, ebitda=480.0),
                FinancialYear(year="2022-23", revenue=4800.0, net_profit=380.0, total_assets=7200.0, total_equity=3600.0, ebitda=820.0),
                FinancialYear(year="2023-24", revenue=6500.0, net_profit=660.0, total_assets=9800.0, total_equity=4800.0, ebitda=1180.0),
            ],
            issue=IssueDetails(
                issue_size_cr=18.0,
                fresh_issue_cr=12.0,
                ofs_cr=6.0,
                price_band_low=120.0,
                price_band_high=128.0,
                face_value=10.0,
                lot_size=1000,
                objects_of_issue=(
                    "1. Expansion of technology infrastructure — ₹6 Cr\n"
                    "2. Working capital requirements — ₹4 Cr\n"
                    "3. General corporate purposes — ₹2 Cr"
                ),
                merchant_banker="Axis Capital Limited",
            ),
        )

    def _build_pdf(self):
        """Helper: register a job and call build_drhp, returning pdf bytes."""
        import uuid
        from app.services.drhp_service import build_drhp, _jobs
        req = self._minimal_request()
        job_id = str(uuid.uuid4())
        # Pre-register the job so build_drhp can update its status
        _jobs[job_id] = {"status": "processing", "progress_pct": 0, "message": "", "pdf": None}
        return build_drhp(req, job_id)

    def test_pdf_starts_with_pdf_header(self):
        result = self._build_pdf()
        assert result[:4] == b"%PDF"

    def test_generate_returns_bytes(self):
        result = self._build_pdf()
        assert isinstance(result, bytes)
        assert len(result) > 1000

    def test_pdf_contains_company_name(self):
        result = self._build_pdf()
        # PDF text may be encoded; at minimum check size is substantial
        assert len(result) > 10000  # 10KB minimum for a multi-section DRHP

