"""Smoke test for schema Optional[float] fix and ratio engine None handling."""
import sys
sys.path.insert(0, ".")

from app.schemas.drhp_v2 import ExtendedFinancialYear
from app.ai.financial_intelligence import compute_ratios_for_year

# Test 1: Default field values should now be None, not 0.0
fy_no_data = ExtendedFinancialYear(year="2023-24")
assert fy_no_data.revenue is None, "FAIL: revenue default should be None, got " + str(fy_no_data.revenue)
assert fy_no_data.net_profit is None, "FAIL: net_profit default should be None, got " + str(fy_no_data.net_profit)
assert fy_no_data.total_assets is None, "FAIL: total_assets default should be None, got " + str(fy_no_data.total_assets)
assert fy_no_data.total_equity is None, "FAIL: total_equity default should be None, got " + str(fy_no_data.total_equity)
print("PASS: Schema defaults are correctly None (not 0.0)")

# Test 2: Explicit zero should remain zero
fy_explicit_zero = ExtendedFinancialYear(year="2022-23", revenue=0.0, net_profit=0.0)
assert fy_explicit_zero.revenue == 0.0, "FAIL: explicit 0 should stay 0"
assert fy_explicit_zero.net_profit == 0.0, "FAIL: explicit 0 should stay 0"
print("PASS: Explicit zero values remain as 0.0 (not None)")

# Test 3: Ratio engine returns 'Missing Information' for missing fields
ratios = compute_ratios_for_year(fy_no_data)
pat_margin = next((r for r in ratios if r.name == "PAT Margin"), None)
assert pat_margin is not None, "FAIL: PAT Margin ratio not found"
assert pat_margin.formatted_value == "Missing Information", "FAIL: PAT Margin should be Missing Information, got: " + str(pat_margin.formatted_value)
print("PASS: Ratio engine returns 'Missing Information' for missing fields")

# Test 4: Ratio engine computes correctly with real data
fy_real = ExtendedFinancialYear(
    year="2023-24",
    revenue=5000.0,
    net_profit=400.0,
    ebitda=850.0,
    total_assets=3000.0,
    total_equity=2000.0,
)
ratios_real = compute_ratios_for_year(fy_real)
pat_margin_real = next((r for r in ratios_real if r.name == "PAT Margin"), None)
assert pat_margin_real is not None
assert pat_margin_real.value is not None, "FAIL: PAT Margin should have computed value"
expected_pat_margin = 400.0 / 5000.0 * 100
assert abs(pat_margin_real.value - expected_pat_margin) < 0.001, "FAIL: Expected " + str(expected_pat_margin) + "%, got " + str(pat_margin_real.value)
print("PASS: PAT Margin computed correctly: " + pat_margin_real.formatted_value + " (expected " + str(round(expected_pat_margin, 2)) + "%)")

# Test 5: Section generator builds context without crash on None fields
from app.schemas.drhp_v2 import DrhpRequestV2, ExtendedCompanyProfile, ExtendedIssueDetails
from app.ai.section_generator import _build_company_context

co = ExtendedCompanyProfile(
    name="Test Corp Ltd",
    cin="U12345MH2020PLC123456",
    pan="AAACT1234A",
    incorporation_date="2020-01-01",
    sector="Manufacturing",
    registered_address="123 Test Street, Mumbai, Maharashtra",
    description="A test company",
)
iss = ExtendedIssueDetails(
    issue_size_cr=50.0,
    fresh_issue_cr=30.0,
    ofs_cr=20.0,
    merchant_banker="Test MB Ltd",
    objects_of_issue="General corporate purposes",
    face_value=10.0,
    price_band_low=100.0,
    price_band_high=110.0,
)
req = DrhpRequestV2(
    company=co,
    issue=iss,
    financials=[fy_no_data],
)
ctx = _build_company_context(req)
assert "Not Provided" in ctx, "FAIL: Context should contain 'Not Provided' for None financials"
assert "0.00L" not in ctx, "FAIL: Context should NOT show 0.00L for missing data — got: " + ctx
print("PASS: Section context correctly shows 'Not Provided' instead of 0.00L")

print("\nAll 5 tests PASSED!")
