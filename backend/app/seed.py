"""
Seed script — populates the database with demo data for hackathon demo.
Run INSIDE the backend container:
    docker compose exec backend python -m app.seed
Or directly:
    cd backend && python -m app.seed
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.company import Company
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.compliance_check import ComplianceCheck
from app.models.validation_result import ValidationResult
from app.utils.security import hash_password

# ──────────────────────────────────────────────────────────────────────────────
# Demo data constants
# ──────────────────────────────────────────────────────────────────────────────

DEMO_USER = {
    "id": str(uuid.uuid4()),
    "email": "demo@ipocolpilot.ai",
    "password": "Demo@1234",
    "full_name": "Demo Analyst",
    "role": "analyst",
}

DEMO_COMPANY = {
    "id": str(uuid.uuid4()),
    "name": "Acme Technologies Private Limited",
    "cin": "U72900MH2020PTC345678",
    "pan": "AACCA1234B",
    "industry": "Technology",
}

DEMO_WORKSPACE = {
    "id": str(uuid.uuid4()),
    "name": "Acme Technologies IPO 2026",
    "status": "draft",
}

DEMO_DOCUMENTS = [
    {
        "id": str(uuid.uuid4()),
        "name": "Audited Financial Statements FY 2023-24.pdf",
        "doc_type": "financial_statement",
        "file_path": "uploads/demo/financial_statement_fy2024.pdf",
        "file_size": 2_450_000,
        "mime_type": "application/pdf",
        "status": "validated",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Prospectus Draft v1.0.pdf",
        "doc_type": "prospectus_draft",
        "file_path": "uploads/demo/prospectus_draft_v1.pdf",
        "file_size": 5_120_000,
        "mime_type": "application/pdf",
        "status": "validated",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Statutory Auditor Report.pdf",
        "doc_type": "auditor_report",
        "file_path": "uploads/demo/auditor_report.pdf",
        "file_size": 890_000,
        "mime_type": "application/pdf",
        "status": "validated",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Shareholding Pattern.xlsx",
        "doc_type": "shareholding_pattern",
        "file_path": "uploads/demo/shareholding_pattern.xlsx",
        "file_size": 120_000,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "status": "uploaded",
    },
]

COMPLIANCE_SEED = [
    # PASS checks
    ("ICDR_REG_229", "SME IPO Applicability — Post-issue paid up capital ≤ ₹25 crore", "pass",
     "Company's proposed post-issue paid-up capital of ₹12.5 crore is within the ₹25 crore limit mandated by Regulation 229.",
     {"source": "Prospectus Draft v1.0, Page 4", "value": "₹12.5 crore"}),
    ("ICDR_REG_230_a", "SME Eligibility — 3-year operational track record", "pass",
     "Company incorporated in 2018 with 6+ years of operations. Exceeds the minimum 3-year requirement under Regulation 230(1)(a).",
     {"incorporated": "2018", "years_of_operation": 6}),
    ("ICDR_REG_230_b", "SME Eligibility — Tangible assets ≥ ₹1.5 crore", "pass",
     "Latest audited balance sheet shows tangible assets of ₹18.2 crore, well above the ₹1.5 crore threshold.",
     {"tangible_assets": "₹18.2 crore", "threshold": "₹1.5 crore"}),
    ("ICDR_REG_230_c", "Positive net worth confirmed", "pass",
     "Net worth of ₹9.8 crore reported in FY 2023-24 audited financials. Condition satisfied.",
     {"net_worth": "₹9.8 crore", "fy": "2023-24"}),
    ("ICDR_REG_231", "Promoters' Contribution — Minimum 20% post-issue", "pass",
     "Promoters hold 62.5% post-issue stake per shareholding pattern document. Exceeds 20% minimum requirement.",
     {"promoter_stake": "62.5%", "minimum": "20%"}),
    ("ICDR_REG_232", "Lock-in Period — 3 years on minimum contribution", "pass",
     "Lock-in certificate confirms promoter contribution of 20% locked for 3 years from allotment date.",
     {"lock_in_years": 3, "locked_amount": "20%"}),
    ("ICDR_REG_235", "Issue Size — Between ₹50L and ₹25Cr", "pass",
     "Proposed issue size of ₹8.5 crore falls within the permissible range of ₹50 lakhs to ₹25 crore.",
     {"issue_size": "₹8.5 crore"}),
    ("ICDR_REG_237", "Market Maker — Mandatory appointment confirmed", "pass",
     "Market Maker Agreement with NSE Emerge registered broker attached as Annexure 6 to the prospectus.",
     {"market_maker": "XYZ Securities Limited", "exchange": "NSE Emerge"}),
    ("ICDR_REG_239", "Promoter Disclosures — Full profiles included", "pass",
     "Prospectus Section 7 contains complete profiles for 3 promoters including shareholding, experience, and other directorships.",
     {"promoters_disclosed": 3}),
    ("ICDR_REG_242", "Financial Statements — 3-year audited accounts present", "pass",
     "Restated audited financial statements for FY 2021-22, 2022-23, and 2023-24 included as Annexure 1.",
     {"years_covered": ["FY 2021-22", "FY 2022-23", "FY 2023-24"]}),
    ("ICDR_REG_244", "Corporate Governance — Audit Committee constituted", "pass",
     "Board composition shows 4 directors including 2 independent directors. Audit Committee with majority independents confirmed.",
     {"total_directors": 4, "independent_directors": 2}),

    # WARNING checks
    ("ICDR_REG_230_d", "Distributable profits in 2 of last 3 years", "warning",
     "Profitability data shows profits in FY 2022-23 and FY 2023-24, but FY 2021-22 shows a net loss. Mandatory market maker required. Condition met with exception.",
     {"profitable_years": ["FY 2022-23", "FY 2023-24"], "loss_year": "FY 2021-22"}),
    ("ICDR_REG_234", "Offer Document — All mandatory sections present", "warning",
     "Most mandatory sections per Schedule IV are present. However, 'Statement of Tax Benefits' (Section 3) appears incomplete — CA certification signature is missing.",
     {"missing": "CA signature on Statement of Tax Benefits", "section": "3"}),
    ("ICDR_REG_240", "Litigation Disclosures — Outstanding matters", "warning",
     "One pending civil suit (₹45 lakhs) against the company in Mumbai High Court detected. Disclosure present but mitigation commentary is weak.",
     {"pending_suits": 1, "amount": "₹45 lakhs", "court": "Mumbai High Court"}),
    ("ICDR_REG_241", "Related Party Transactions — 3-year disclosure", "warning",
     "RPT disclosure in Annexure covers only 2 years (FY 2022-23 and FY 2023-24). FY 2021-22 RPT data is missing as required by Regulation 241.",
     {"years_disclosed": 2, "required": 3, "missing_year": "FY 2021-22"}),
    ("ICDR_REG_243", "Objects of Issue — Fund utilization schedule", "warning",
     "Objects section lists 4 purposes but the implementation schedule table is missing. Regulation 243 requires a phased deployment timeline.",
     {"objects_listed": 4, "missing": "implementation schedule table"}),

    # FAIL checks
    ("ICDR_REG_233", "Pre-issue Obligations — Lead Manager Agreement", "fail",
     "No executed Lead Manager Agreement found in the uploaded documents. SEBI requires a SEBI-registered Merchant Banker as Lead Manager. This is a critical non-compliance.",
     {"required": "Lead Manager Agreement", "status": "NOT FOUND"}),
    ("ICDR_REG_245", "Declarations — All mandatory signatories", "fail",
     "Declaration page is missing signature from Compliance Officer. Section requires declarations from Board, Auditors, Lead Manager, and Compliance Officer.",
     {"missing_signatory": "Compliance Officer", "page": "Cover Page"}),
    ("ICDR_REG_236", "Allotment — 50% reserved for retail investors", "fail",
     "Issue allocation table shows 45% reserved for retail investors. SEBI mandates minimum 50% of net offer to Retail Individual Investors (RII).",
     {"current": "45%", "required": "50%", "shortfall": "5%"}),
]


async def seed(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    # 1. User
    user = User(
        id=DEMO_USER["id"],
        email=DEMO_USER["email"],
        password_hash=hash_password(DEMO_USER["password"]),
        full_name=DEMO_USER["full_name"],
        role=DEMO_USER["role"],
        created_at=now,
        updated_at=now,
    )
    db.add(user)

    # 2. Company
    company = Company(
        id=DEMO_COMPANY["id"],
        name=DEMO_COMPANY["name"],
        cin=DEMO_COMPANY["cin"],
        pan=DEMO_COMPANY["pan"],
        industry=DEMO_COMPANY["industry"],
        created_by=DEMO_USER["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(company)

    # 3. Workspace
    workspace = Workspace(
        id=DEMO_WORKSPACE["id"],
        company_id=DEMO_COMPANY["id"],
        name=DEMO_WORKSPACE["name"],
        status=DEMO_WORKSPACE["status"],
        created_by=DEMO_USER["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(workspace)

    await db.flush()

    # 4. Documents
    doc_ids = []
    for doc_data in DEMO_DOCUMENTS:
        doc = Document(
            id=doc_data["id"],
            workspace_id=DEMO_WORKSPACE["id"],
            name=doc_data["name"],
            doc_type=doc_data["doc_type"],
            file_path=doc_data["file_path"],
            file_size=doc_data["file_size"],
            mime_type=doc_data["mime_type"],
            status=doc_data["status"],
            uploaded_by=DEMO_USER["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(doc)
        doc_ids.append(doc_data["id"])

    # 5. Validation results for validated docs
    for doc_data in DEMO_DOCUMENTS:
        if doc_data["status"] == "validated":
            vr = ValidationResult(
                id=str(uuid.uuid4()),
                document_id=doc_data["id"],
                status="completed",
                issues=[
                    {"type": "missing_disclosure", "severity": "medium",
                     "description": "Risk factor section lacks quantitative impact assessment",
                     "page": 12, "rule": "ICDR_REG_234"},
                    {"type": "formatting", "severity": "low",
                     "description": "Page numbers inconsistent in footer after page 45",
                     "page": 45, "rule": "ICDR_REG_234"},
                ],
                missing_info=[
                    {"field": "EBITDA margin trend", "section": "Financial Highlights",
                     "required_by": "ICDR_REG_242", "description": "3-year EBITDA margin comparison table missing"},
                ],
                summary=(
                    "Document analysis complete. 2 issues found — 1 medium severity formatting issue "
                    "in Risk Factors section and 1 minor formatting inconsistency. 1 missing data "
                    "field identified in Financial Highlights. Overall document quality is good with "
                    "minor corrections required before final filing."
                ),
                ai_model="gpt-4o-mini",
                created_at=now,
            )
            db.add(vr)

    # 6. Compliance checks
    for check_type, regulation, status, reasoning, evidence in COMPLIANCE_SEED:
        check = ComplianceCheck(
            id=str(uuid.uuid4()),
            workspace_id=DEMO_WORKSPACE["id"],
            check_type=check_type,
            regulation=regulation,
            status=status,
            evidence=evidence,
            ai_reasoning=reasoning,
            created_at=now,
            updated_at=now,
        )
        db.add(check)

    await db.commit()
    print("✅ Seed completed successfully!")
    print(f"   Demo login: {DEMO_USER['email']} / {DEMO_USER['password']}")
    print(f"   Workspace ID: {DEMO_WORKSPACE['id']}")


async def main() -> None:
    from app.database import create_tables
    await create_tables()
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
