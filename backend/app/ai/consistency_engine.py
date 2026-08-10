"""
Cross-Section Consistency Engine
Validates mathematical and logical consistency across all DRHP data before PDF generation.

DESIGN RULES:
- 20 independent cross-checks
- Critical errors BLOCK PDF generation
- Warnings are surfaced but do not block
- Never silently suppress findings
- Each check has a unique ID for traceability
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.schemas.drhp_v2 import (
    ConsistencyFlag,
    ConsistencyReport,
    DrhpRequestV2,
)

logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # 1% tolerance for floating-point financial comparisons


def _approx_eq(a: float, b: float, tol: float = TOLERANCE) -> bool:
    """True if |a - b| / max(|a|, |b|, 1) <= tol."""
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "Not provided"
    return f"₹{v:,.2f}"


class ConsistencyEngine:
    """
    Runs 20 cross-section consistency checks on a DrhpRequestV2.
    Returns a ConsistencyReport indicating whether PDF generation can proceed.
    """

    def __init__(self, req: DrhpRequestV2):
        self.req = req
        self.errors: List[ConsistencyFlag] = []
        self.warnings: List[ConsistencyFlag] = []
        self.info_flags: List[ConsistencyFlag] = []
        self.total_checks = 0
        self.passed_checks = 0

    def _error(self, check_name: str, description: str, affected: List[str],
               expected: Optional[str] = None, actual: Optional[str] = None,
               fix: Optional[str] = None) -> None:
        self.errors.append(ConsistencyFlag(
            severity="critical",
            check_name=check_name,
            description=description,
            affected_sections=affected,
            expected_value=expected,
            actual_value=actual,
            recommended_fix=fix,
        ))

    def _warn(self, check_name: str, description: str, affected: List[str],
              expected: Optional[str] = None, actual: Optional[str] = None,
              fix: Optional[str] = None) -> None:
        self.warnings.append(ConsistencyFlag(
            severity="warning",
            check_name=check_name,
            description=description,
            affected_sections=affected,
            expected_value=expected,
            actual_value=actual,
            recommended_fix=fix,
        ))

    def _info(self, check_name: str, description: str, affected: List[str]) -> None:
        self.info_flags.append(ConsistencyFlag(
            severity="info",
            check_name=check_name,
            description=description,
            affected_sections=affected,
        ))

    def _check(self, passed: bool) -> None:
        self.total_checks += 1
        if passed:
            self.passed_checks += 1

    # ── Check 1: Promoter holdings sum ─────────────────────────────────────
    def _check_promoter_holdings_sum(self) -> None:
        promoters = self.req.promoters
        if not promoters:
            self._warn(
                "PROMOTER_HOLDINGS_SUM",
                "No promoter details provided — shareholding pattern cannot be validated.",
                ["Shareholding Pattern", "Promoters"],
                fix="Add at least one promoter with holding_pct",
            )
            self._check(False)
            return

        total_pct = sum(p.holding_pct for p in promoters)
        issue = self.req.issue

        # Pre-issue promoter holding should be <= 100%
        if total_pct > 100.0 + TOLERANCE:
            self._error(
                "PROMOTER_HOLDINGS_SUM",
                f"Total promoter holdings ({total_pct:.2f}%) exceed 100%. "
                "Sum of all promoter holding_pct values must not exceed 100.",
                ["Capital Structure", "Shareholding Pattern", "Promoters"],
                expected="<= 100%",
                actual=f"{total_pct:.2f}%",
                fix="Verify individual promoter holding percentages and correct arithmetic.",
            )
            self._check(False)
        else:
            self._check(True)
            if total_pct < 50.0:
                self._warn(
                    "PROMOTER_MINIMUM_HOLDING",
                    f"Total promoter pre-issue holding is {total_pct:.2f}%. "
                    "SEBI requires minimum 20% promoter holding post-issue for SME IPOs. "
                    "Verify post-issue dilution does not breach SEBI minimum.",
                    ["Promoters", "Capital Structure"],
                    fix="Confirm post-issue promoter holding satisfies SEBI ICDR Regulation 268.",
                )

    # ── Check 2: Issue structure reconciliation ─────────────────────────────
    def _check_issue_structure(self) -> None:
        iss = self.req.issue
        total = iss.fresh_issue_cr + iss.ofs_cr
        declared = iss.issue_size_cr

        if abs(declared) < 0.001:
            self._warn(
                "ISSUE_STRUCTURE_RECONCILE",
                "Issue size is zero or not provided.",
                ["Issue Summary", "Objects of the Issue"],
            )
            self._check(False)
            return

        if not _approx_eq(total, declared):
            self._error(
                "ISSUE_STRUCTURE_RECONCILE",
                f"Fresh Issue ({_fmt(iss.fresh_issue_cr)} Cr) + OFS ({_fmt(iss.ofs_cr)} Cr) "
                f"= {_fmt(total)} Cr does not match declared Issue Size ({_fmt(declared)} Cr).",
                ["Cover Page", "Issue Summary", "Capital Structure", "Objects of the Issue"],
                expected=f"Fresh Issue + OFS = {_fmt(declared)} Cr",
                actual=f"Sum = {_fmt(total)} Cr",
                fix="Correct fresh_issue_cr or ofs_cr to reconcile with issue_size_cr.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 3: Use-of-proceeds reconciliation ─────────────────────────────
    def _check_use_of_proceeds(self) -> None:
        iss = self.req.issue
        if not iss.use_of_proceeds_structured:
            self._info(
                "USE_OF_PROCEEDS_STRUCTURED",
                "Structured use-of-proceeds breakdown not provided. "
                "Objects of Issue section will use narrative text only.",
                ["Objects of the Issue"],
            )
            self._check(True)
            return

        total_proceeds = sum(item.amount_lakhs for item in iss.use_of_proceeds_structured)
        fresh_issue_lakhs = iss.fresh_issue_cr * 100  # Convert Crore to Lakhs

        if fresh_issue_lakhs > 0 and not _approx_eq(total_proceeds, fresh_issue_lakhs):
            self._warn(
                "USE_OF_PROCEEDS_RECONCILE",
                f"Sum of use-of-proceeds items ({_fmt(total_proceeds)} Lakhs) does not match "
                f"Fresh Issue size ({_fmt(fresh_issue_lakhs)} Lakhs). Note: OFS proceeds go to selling shareholders, "
                "not the company.",
                ["Objects of the Issue"],
                expected=f"{_fmt(fresh_issue_lakhs)} Lakhs",
                actual=f"{_fmt(total_proceeds)} Lakhs",
                fix="Verify use-of-proceeds amounts sum to the fresh issue amount (OFS proceeds excluded).",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 4: Financial year sequence ───────────────────────────────────
    def _check_financial_year_sequence(self) -> None:
        fys = self.req.financials
        if len(fys) < 2:
            self._info(
                "FINANCIAL_YEAR_SEQUENCE",
                "Only one financial year provided. Three years required by SEBI for SME IPO.",
                ["Financial Statements"],
            )
            self._check(True)
            return

        years = [fy.year for fy in fys]
        for i in range(1, len(years)):
            if years[i] <= years[i - 1]:
                self._error(
                    "FINANCIAL_YEAR_SEQUENCE",
                    f"Financial years are not in ascending order: {years}. "
                    "Years must be sequential and non-repeating.",
                    ["Financial Statements"],
                    expected="Ascending order e.g. ['2021-22', '2022-23', '2023-24']",
                    actual=str(years),
                    fix="Sort financial years in ascending order.",
                )
                self._check(False)
                return
        self._check(True)

    # ── Check 5: Balance sheet equation ────────────────────────────────────
    def _check_balance_sheet_equation(self) -> None:
        """Assets = Liabilities + Equity"""
        if not self.req.financials:
            self._check(True)
            return

        all_passed = True
        for fy in self.req.financials:
            if fy.total_assets and fy.total_equity:
                implied_liabilities = fy.total_assets - fy.total_equity
                if fy.total_liabilities is not None:
                    if not _approx_eq(implied_liabilities, fy.total_liabilities, 0.02):
                        self._warn(
                            f"BALANCE_SHEET_EQUATION_{fy.year}",
                            f"Balance sheet does not balance in {fy.year}: "
                            f"Assets ({_fmt(fy.total_assets)}) - Equity ({_fmt(fy.total_equity)}) "
                            f"= {_fmt(implied_liabilities)} ≠ Reported Liabilities ({_fmt(fy.total_liabilities)})",
                            ["Financial Statements", "Balance Sheet"],
                            expected=f"Liabilities = {_fmt(implied_liabilities)}",
                            actual=f"Provided liabilities = {_fmt(fy.total_liabilities)}",
                            fix="Verify total_assets, total_equity, and total_liabilities for internal consistency.",
                        )
                        all_passed = False
        self._check(all_passed)

    # ── Check 6: EBITDA derivation consistency ──────────────────────────────
    def _check_ebitda_consistency(self) -> None:
        all_passed = True
        for fy in self.req.financials:
            if fy.ebit is not None and fy.depreciation is not None and fy.ebitda is not None:
                derived_ebitda = fy.ebit + fy.depreciation
                if not _approx_eq(derived_ebitda, fy.ebitda, 0.02):
                    self._warn(
                        f"EBITDA_DERIVATION_{fy.year}",
                        f"EBITDA inconsistency in {fy.year}: EBIT ({_fmt(fy.ebit)}) + D&A ({_fmt(fy.depreciation)}) "
                        f"= {_fmt(derived_ebitda)} but reported EBITDA = {_fmt(fy.ebitda)}",
                        ["Financial Statements", "MDA"],
                        fix="Reconcile EBIT, Depreciation, and EBITDA figures for mathematical consistency.",
                    )
                    all_passed = False
        self._check(all_passed)

    # ── Check 7: PAT vs PBT vs Tax consistency ─────────────────────────────
    def _check_pat_pbt_tax(self) -> None:
        all_passed = True
        for fy in self.req.financials:
            if fy.pbt is not None and fy.tax_expense is not None and fy.net_profit is not None:
                derived_pat = fy.pbt - fy.tax_expense
                if not _approx_eq(derived_pat, fy.net_profit, 0.02):
                    self._warn(
                        f"PAT_DERIVATION_{fy.year}",
                        f"PAT inconsistency in {fy.year}: PBT ({_fmt(fy.pbt)}) - Tax ({_fmt(fy.tax_expense)}) "
                        f"= {_fmt(derived_pat)} but reported PAT = {_fmt(fy.net_profit)}",
                        ["Financial Statements"],
                        fix="Reconcile PBT, Tax Expense, and PAT for mathematical consistency.",
                    )
                    all_passed = False
        self._check(all_passed)

    # ── Check 8: Price band validity ───────────────────────────────────────
    def _check_price_band(self) -> None:
        iss = self.req.issue
        if iss.price_band_low > 0 and iss.price_band_high > 0:
            if iss.price_band_low > iss.price_band_high:
                self._error(
                    "PRICE_BAND_VALIDITY",
                    f"Price band floor ({iss.price_band_low}) is greater than cap ({iss.price_band_high}).",
                    ["Cover Page", "Issue Summary", "Basis for Issue Price"],
                    expected=f"Floor <= Cap",
                    actual=f"Floor={iss.price_band_low}, Cap={iss.price_band_high}",
                    fix="Correct price_band_low and price_band_high values.",
                )
                self._check(False)
                return
            spread = (iss.issue_size_cr / iss.price_band_high * 100) if iss.price_band_high > 0 else 0
            if (iss.price_band_high - iss.price_band_low) / iss.price_band_high > 0.10:
                self._warn(
                    "PRICE_BAND_SPREAD",
                    f"Price band spread exceeds 10% of cap price. SEBI SME IPOs typically have a "
                    f"narrow band. Verify this is intentional.",
                    ["Issue Summary"],
                )
        self._check(True)

    # ── Check 9: Post-issue promoter SEBI minimum ──────────────────────────
    def _check_post_issue_promoter_min(self) -> None:
        iss = self.req.issue
        if iss.post_issue_promoter_holding_pct is not None:
            if iss.post_issue_promoter_holding_pct < 20.0:
                self._error(
                    "POST_ISSUE_PROMOTER_MIN",
                    f"Post-issue promoter holding ({iss.post_issue_promoter_holding_pct:.2f}%) is below "
                    "SEBI ICDR minimum of 20% for SME IPOs.",
                    ["Capital Structure", "Shareholding Pattern"],
                    expected=">= 20%",
                    actual=f"{iss.post_issue_promoter_holding_pct:.2f}%",
                    fix="Review fresh issue quantum — reduce dilution to maintain >=20% promoter holding post-issue.",
                )
                self._check(False)
            else:
                self._check(True)
        else:
            self._info(
                "POST_ISSUE_PROMOTER_NOT_PROVIDED",
                "post_issue_promoter_holding_pct not provided. Cannot verify SEBI minimum 20% requirement.",
                ["Capital Structure"],
            )
            self._check(True)

    # ── Check 10: Issue size SEBI minimum ──────────────────────────────────
    def _check_issue_size_minimum(self) -> None:
        # SEBI SME IPO minimum post-issue paid-up capital is ₹3 Crore (as of 2018 ICDR)
        if self.req.issue.issue_size_cr < 3.0:
            self._warn(
                "ISSUE_SIZE_MINIMUM",
                f"Issue size ({_fmt(self.req.issue.issue_size_cr)} Cr) may be below SEBI SME minimum thresholds. "
                "Verify compliance with applicable SEBI ICDR regulations for minimum issue size.",
                ["Issue Summary", "Cover Page"],
                fix="Verify post-issue paid-up capital will be at least ₹3 Crore.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 11: Minimum 3 financial years ────────────────────────────────
    def _check_minimum_financial_years(self) -> None:
        n = len(self.req.financials)
        if n < 3:
            self._warn(
                "MINIMUM_FINANCIAL_YEARS",
                f"Only {n} financial year(s) provided. SEBI requires 3 years of audited financials for SME IPOs.",
                ["Financial Statements"],
                expected="3 years",
                actual=f"{n} year(s)",
                fix="Add financial data for 3 complete audited financial years.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 12: Company name consistency ─────────────────────────────────
    def _check_company_name_provided(self) -> None:
        co = self.req.company
        if not co.name or len(co.name.strip()) < 3:
            self._error(
                "COMPANY_NAME_REQUIRED",
                "Company name is missing or too short. All DRHP sections require the legal company name.",
                ["Cover Page", "All Sections"],
                fix="Provide the full legal name of the company.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 13: CIN format and state code cross-check ──────────────────────
    def _check_cin_format(self) -> None:
        """
        Validates CIN format (21 characters: L/U + 5 digits + 2-letter state + 4 digits + 3-letter type + 6 digits)
        and cross-checks the state code in the CIN against the registered address state.
        """
        import re
        # Map of 2-letter CIN state codes → state names (partial list of common states)
        STATE_CODE_MAP = {
            "MH": ["Maharashtra", "Mumbai", "Pune", "Nagpur"],
            "DL": ["Delhi", "New Delhi"],
            "KA": ["Karnataka", "Bangalore", "Bengaluru"],
            "TN": ["Tamil Nadu", "Chennai"],
            "GJ": ["Gujarat", "Ahmedabad", "Surat"],
            "WB": ["West Bengal", "Kolkata"],
            "RJ": ["Rajasthan", "Jaipur"],
            "UP": ["Uttar Pradesh", "Lucknow", "Noida", "Ghaziabad"],
            "HR": ["Haryana", "Gurugram", "Gurgaon", "Faridabad"],
            "PB": ["Punjab", "Chandigarh", "Amritsar"],
            "AP": ["Andhra Pradesh", "Hyderabad", "Visakhapatnam"],
            "TS": ["Telangana", "Hyderabad"],
            "KL": ["Kerala", "Thiruvananthapuram", "Kochi"],
            "MP": ["Madhya Pradesh", "Bhopal", "Indore"],
            "OD": ["Odisha", "Bhubaneswar"],
        }
        cin = self.req.company.cin
        if not cin or len(cin) != 21:
            self._warn(
                "CIN_FORMAT",
                f"CIN '{cin}' is not 21 characters. Valid format: L/U + 5 digits + 2-letter state + "
                "4-digit year + 3-letter entity type + 6-digit sequence.",
                ["Cover Page", "Company Overview"],
                fix="Provide a valid MCA-issued CIN (21 characters).",
            )
            self._check(False)
            return

        cin_pattern = re.compile(r'^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$')
        if not cin_pattern.match(cin):
            self._warn(
                "CIN_FORMAT",
                f"CIN '{cin}' does not match the standard MCA format "
                "(L/U + 5 digits + state code + 4-digit year + entity type + 6-digit sequence).",
                ["Cover Page", "Company Overview"],
                fix="Provide a valid MCA-issued CIN.",
            )
            self._check(False)
            return

        # Cross-check: state code in CIN vs registered address
        cin_state_code = cin[7:9]
        address = self.req.company.registered_address or ""
        if cin_state_code in STATE_CODE_MAP:
            expected_keywords = STATE_CODE_MAP[cin_state_code]
            address_upper = address.upper()
            # Check if any expected state/city keyword appears in the address
            if not any(kw.upper() in address_upper for kw in expected_keywords):
                self._warn(
                    "CIN_STATE_ADDRESS_MISMATCH",
                    f"CIN state code '{cin_state_code}' (suggests {expected_keywords[0]}) does not appear "
                    f"to match the registered address: '{address[:80]}...'. "
                    "SEBI requires CIN to reflect the state of incorporation, consistent with the registered office address.",
                    ["Cover Page", "Company Overview", "Corporate Information"],
                    expected=f"Address should mention a location in {expected_keywords[0]}",
                    actual=f"Address: {address[:60]}",
                    fix="Verify that the CIN state code matches the state of the registered office address. "
                        "If the company has relocated, file for CIN state amendment with MCA.",
                )
        self._check(True)


    # ── Check 14: Face value — SEBI-approved denominations only ─────────────
    def _check_face_value(self) -> None:
        fv = self.req.issue.face_value
        SEBI_ALLOWED = [1.0, 2.0, 5.0, 10.0]
        if fv not in SEBI_ALLOWED:
            self._error(
                "FACE_VALUE_SEBI",
                f"Face value ₹{fv} is not a SEBI-permitted denomination. "
                f"SEBI ICDR Regulations permit face values of ₹1, ₹2, ₹5, or ₹10 only.",
                ["Capital Structure", "Cover Page", "Issue Summary"],
                expected=f"One of: {SEBI_ALLOWED}",
                actual=f"₹{fv}",
                fix="Set face_value to one of the SEBI-approved denominations: ₹1, ₹2, ₹5, or ₹10.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 15: Lot size validity ─────────────────────────────────────────
    def _check_lot_size(self) -> None:
        ls = self.req.issue.lot_size
        if ls > 0 and ls % 1 == 0:
            # SME lot size must ensure minimum application value of ~₹1 Lakh (SEBI guideline)
            min_app_value = ls * self.req.issue.price_band_high if self.req.issue.price_band_high else 0
            if min_app_value > 0 and min_app_value < 100000:
                self._warn(
                    "LOT_SIZE_MINIMUM_APPLICATION",
                    f"Minimum application amount at cap price: ₹{min_app_value:,.0f}. "
                    "SEBI SME IPOs should have minimum application amount of approximately ₹1 Lakh.",
                    ["Issue Summary"],
                    fix="Increase lot_size so that lot_size × cap_price ≈ ₹1,00,000.",
                )
                self._check(False)
                return
        self._check(True)

    # ── Check 16: Merchant banker name provided ─────────────────────────────
    def _check_merchant_banker(self) -> None:
        mb = self.req.issue.merchant_banker
        if not mb or len(mb.strip()) < 3:
            self._warn(
                "MERCHANT_BANKER_REQUIRED",
                "Lead manager / merchant banker name not provided. Mandatory SEBI disclosure.",
                ["Cover Page", "Issue Summary"],
                fix="Provide the name of the SEBI-registered lead merchant banker.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 17: Shares reconciliation ────────────────────────────────────
    def _check_share_reconciliation(self) -> None:
        iss = self.req.issue
        if all(v is not None for v in [iss.pre_issue_shares, iss.fresh_issue_shares, iss.post_issue_shares]):
            expected_post = iss.pre_issue_shares + iss.fresh_issue_shares
            if not _approx_eq(float(expected_post), float(iss.post_issue_shares), 0.001):
                self._error(
                    "SHARE_COUNT_RECONCILE",
                    f"Pre-issue shares ({iss.pre_issue_shares:,}) + Fresh Issue shares ({iss.fresh_issue_shares:,}) "
                    f"= {expected_post:,} ≠ Post-issue shares ({iss.post_issue_shares:,}).",
                    ["Capital Structure", "Shareholding Pattern"],
                    expected=f"{expected_post:,}",
                    actual=f"{iss.post_issue_shares:,}",
                    fix="Verify pre-issue, fresh issue, and post-issue share counts.",
                )
                self._check(False)
            else:
                self._check(True)
        else:
            self._info(
                "SHARE_COUNT_NOT_PROVIDED",
                "pre_issue_shares, fresh_issue_shares, or post_issue_shares not provided — "
                "cannot perform share count reconciliation.",
                ["Capital Structure"],
            )
            self._check(True)

    # ── Check 18: Revenue trend plausibility ───────────────────────────────
    def _check_revenue_plausibility(self) -> None:
        fys = self.req.financials
        if len(fys) < 2:
            self._check(True)
            return

        for i in range(1, len(fys)):
            prev = fys[i - 1].revenue
            curr = fys[i].revenue
            if prev > 0 and curr > 0:
                change_pct = abs(curr - prev) / prev * 100
                if change_pct > 500:
                    self._warn(
                        f"REVENUE_PLAUSIBILITY_{fys[i].year}",
                        f"Revenue change from {fys[i-1].year} to {fys[i].year} is {change_pct:.0f}% — "
                        "unusually large. Please verify data accuracy.",
                        ["Financial Statements", "MDA"],
                        fix="Verify revenue figures and units (Lakhs vs Crore).",
                    )
        self._check(True)

    # ── Check 19: Legal proceedings — material amount sanity ───────────────
    def _check_legal_proceedings(self) -> None:
        legal = self.req.legal_proceedings
        if not legal:
            self._info(
                "LEGAL_PROCEEDINGS_NOT_PROVIDED",
                "No legal proceedings provided. Outstanding Litigation section will state 'None as disclosed by management'.",
                ["Outstanding Litigation"],
            )
            self._check(True)
            return

        for lp in legal:
            if lp.amount_involved_lakhs is not None and lp.amount_involved_lakhs > 10000:
                self._warn(
                    "LEGAL_PROCEEDINGS_MATERIAL",
                    f"Legal proceeding involving ₹{lp.amount_involved_lakhs:,.2f} Lakhs before "
                    f"{lp.court_or_tribunal} — this may be material. Ensure adequate disclosure and SEBI notification.",
                    ["Outstanding Litigation"],
                    fix="Disclose fully — amounts > ₹1 Crore are typically material for SME IPOs.",
                )
        self._check(True)

    # ── Check 20: Objects of issue text present ─────────────────────────────
    def _check_objects_of_issue(self) -> None:
        obj = self.req.issue.objects_of_issue
        if not obj or len(obj.strip()) < 50:
            self._warn(
                "OBJECTS_OF_ISSUE_REQUIRED",
                "Objects of the Issue description is very short or missing. "
                "SEBI requires specific, measurable objects with timeline and deployment schedule.",
                ["Objects of the Issue"],
                fix="Provide a detailed description of how IPO proceeds will be used.",
            )
            self._check(False)
        else:
            self._check(True)

    # ── Check 21: Auditor Consistency ───────────────────────────────────────
    def _check_auditor_consistency(self) -> None:
        fys = self.req.financials
        if not fys:
            self._check(True)
            return

        auditors = set()
        missing_auditor = False
        for fy in fys:
            if fy.auditor_name:
                auditors.add(fy.auditor_name.strip().lower())
            else:
                missing_auditor = True
                
        if missing_auditor:
            self._warn(
                "AUDITOR_MISSING",
                "Auditor name is missing for one or more financial years. Restated financials require auditor details.",
                ["Financial Statements"],
            )

        if len(auditors) > 1:
            self._info(
                "AUDITOR_CHANGED",
                "Multiple auditors detected across financial years. Ensure a 'Change in Auditor' disclosure is present if applicable.",
                ["Financial Statements", "General Information"],
            )
        self._check(True)
        
    # ── Check 22: EPS Calculation Plausibility ─────────────────────────────
    def _check_eps_consistency(self) -> None:
        fys = self.req.financials
        for fy in fys:
            if fy.net_profit is not None and fy.shares_outstanding is not None and fy.shares_outstanding > 0:
                # Net profit is in Lakhs (100,000s), shares are in absolute units.
                # EPS = (Net Profit * 100,000) / Shares
                eps = (fy.net_profit * 100000) / fy.shares_outstanding
                if eps > 10000 or eps < -10000:
                    self._warn(
                        f"EPS_PLAUSIBILITY_{fy.year}",
                        f"Calculated EPS for {fy.year} is {eps:.2f}, which is highly unusual. Verify that shares_outstanding is in units (not Lakhs) and net_profit is in Lakhs.",
                        ["Financial Statements"],
                        fix="Verify shares_outstanding unit.",
                    )
        self._check(True)

    # ── Main runner ─────────────────────────────────────────────────────────

    def run_all_checks(self) -> ConsistencyReport:
        """Execute all 20+ consistency checks and return a ConsistencyReport."""
        logger.info("Running consistency engine for company: %s", self.req.company.name)

        checks = [
            self._check_company_name_provided,
            self._check_promoter_holdings_sum,
            self._check_issue_structure,
            self._check_use_of_proceeds,
            self._check_financial_year_sequence,
            self._check_balance_sheet_equation,
            self._check_ebitda_consistency,
            self._check_pat_pbt_tax,
            self._check_price_band,
            self._check_post_issue_promoter_min,
            self._check_issue_size_minimum,
            self._check_minimum_financial_years,
            self._check_cin_format,
            self._check_face_value,
            self._check_lot_size,
            self._check_merchant_banker,
            self._check_share_reconciliation,
            self._check_revenue_plausibility,
            self._check_legal_proceedings,
            self._check_objects_of_issue,
            self._check_auditor_consistency,
            self._check_eps_consistency,
        ]

        for check_fn in checks:
            try:
                check_fn()
            except Exception as exc:
                logger.error("Consistency check %s failed with exception: %s", check_fn.__name__, exc, exc_info=True)
                self._warn(
                    f"CHECK_EXECUTION_ERROR_{check_fn.__name__}",
                    f"Could not complete check '{check_fn.__name__}': {exc}",
                    [],
                )

        has_critical = len(self.errors) > 0

        if has_critical:
            status = "critical_errors"
        elif len(self.warnings) > 0:
            status = "warnings"
        else:
            status = "pass"

        logger.info(
            "Consistency report: %s | %d errors, %d warnings, %d info | %d/%d checks passed",
            status, len(self.errors), len(self.warnings), len(self.info_flags),
            self.passed_checks, self.total_checks,
        )

        return ConsistencyReport(
            status=status,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info_flags,
            total_checks=self.total_checks,
            passed_checks=self.passed_checks,
            can_generate_pdf=not has_critical,   # Block PDF only on critical errors
        )


def run_consistency_checks(req: DrhpRequestV2) -> ConsistencyReport:
    """Convenience function — run all checks and return report."""
    engine = ConsistencyEngine(req)
    return engine.run_all_checks()
