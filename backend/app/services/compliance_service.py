import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_check import ComplianceCheck

# 30 realistic SEBI ICDR / LODR / SME IPO rules
SEBI_RULES: list[dict[str, str]] = [
    {
        "id": "ICDR_REG_6",
        "name": "Eligibility for SME IPO",
        "description": "Post-issue paid-up capital of the company shall not exceed ₹25 crore as per SEBI ICDR Regulations.",
    },
    {
        "id": "ICDR_REG_26",
        "name": "Promoter Contribution & Lock-in",
        "description": "Promoters must contribute minimum 20% of the post-issue capital and lock it in for 3 years.",
    },
    {
        "id": "ICDR_REG_32",
        "name": "Objects of the Issue",
        "description": "Proceeds of the issue must be used for specific disclosed objects; any deviation requires shareholder approval.",
    },
    {
        "id": "ICDR_REG_46",
        "name": "Draft Red Herring Prospectus Filing",
        "description": "DRHP must be filed with SEBI at least 30 days before opening of the issue.",
    },
    {
        "id": "ICDR_REG_57",
        "name": "Price Band Disclosure",
        "description": "The price band must be disclosed in the DRHP and should not vary by more than 20% from the floor price.",
    },
    {
        "id": "ICDR_REG_76",
        "name": "Minimum Application Size",
        "description": "Minimum application and allotment lot size for SME IPO shall be ₹1,00,000.",
    },
    {
        "id": "ICDR_REG_91",
        "name": "Underwriting Requirement",
        "description": "100% underwriting of the issue is mandatory for SME IPOs.",
    },
    {
        "id": "ICDR_REG_106",
        "name": "Market Making Obligation",
        "description": "The lead manager must ensure market making for at least 3 years post listing.",
    },
    {
        "id": "LODR_REG_14",
        "name": "Appointment of Compliance Officer",
        "description": "A qualified Company Secretary must be appointed as Compliance Officer before filing.",
    },
    {
        "id": "LODR_REG_17",
        "name": "Board Composition",
        "description": "At least one-third of the board must comprise independent directors.",
    },
    {
        "id": "LODR_REG_18",
        "name": "Audit Committee Composition",
        "description": "Audit committee must have minimum 3 directors with majority being independent.",
    },
    {
        "id": "LODR_REG_19",
        "name": "Nomination & Remuneration Committee",
        "description": "NRC must be constituted with at least 3 non-executive directors, majority independent.",
    },
    {
        "id": "LODR_REG_20",
        "name": "Stakeholders Relationship Committee",
        "description": "SRC must be constituted; Chairperson shall be a non-executive director.",
    },
    {
        "id": "LODR_REG_21",
        "name": "Risk Management Committee",
        "description": "Listed entities with top 1000 market cap must have an RMC; relevant for post-listing compliance planning.",
    },
    {
        "id": "LODR_REG_23",
        "name": "Related Party Transactions",
        "description": "All RPTs must be approved by the audit committee and disclosed in the DRHP.",
    },
    {
        "id": "LODR_REG_25",
        "name": "Independent Director Obligations",
        "description": "IDs must provide declaration of independence; their appointment requires shareholder approval.",
    },
    {
        "id": "LODR_REG_30",
        "name": "Material Event Disclosure",
        "description": "All material events and information must be disclosed to stock exchanges promptly.",
    },
    {
        "id": "LODR_REG_33",
        "name": "Financial Results Submission",
        "description": "Quarterly and annual financial results must be submitted within stipulated timelines post listing.",
    },
    {
        "id": "ICDR_REG_11",
        "name": "Track Record of Profitability",
        "description": "Company must have distributable profits in at least 2 of the 3 preceding fiscal years.",
    },
    {
        "id": "ICDR_REG_12",
        "name": "Net Tangible Assets",
        "description": "Company must have net tangible assets of at least ₹3 crore in each of the preceding 3 full fiscal years.",
    },
    {
        "id": "ICDR_REG_28",
        "name": "Minimum Public Offer Size",
        "description": "At least 25% of post-issue capital must be offered to public; or 10% with minimum ₹400 crore market cap.",
    },
    {
        "id": "ICDR_REG_49",
        "name": "IPO Grading",
        "description": "Grading of IPO by a SEBI-registered credit rating agency is optional but disclosure is mandatory if obtained.",
    },
    {
        "id": "ICDR_REG_53",
        "name": "Escrow Account Arrangement",
        "description": "IPO proceeds must be placed in an escrow account with a scheduled commercial bank.",
    },
    {
        "id": "ICDR_REG_55",
        "name": "Basis of Allotment",
        "description": "Basis of allotment must be determined as per SEBI guidelines and disclosed in prospectus.",
    },
    {
        "id": "ICDR_REG_60",
        "name": "Refund Mechanism",
        "description": "Refunds must be processed within 15 days of closure of issue for unsuccessful applicants.",
    },
    {
        "id": "ICDR_REG_70",
        "name": "Green Shoe Option",
        "description": "If exercising green shoe option, the stabilising agent must be disclosed in the DRHP.",
    },
    {
        "id": "COMPANIES_ACT_S62",
        "name": "Further Issue of Share Capital",
        "description": "Rights issue and private placement rules under Companies Act 2013 Section 62 must be complied with.",
    },
    {
        "id": "FEMA_20",
        "name": "Foreign Investment Compliance",
        "description": "Any foreign shareholding must comply with FEMA 20 sectoral caps and reporting requirements.",
    },
    {
        "id": "ICDR_REG_78",
        "name": "Reservation for Employees",
        "description": "Reservation for eligible employees shall not exceed 5% of post-issue paid-up capital.",
    },
    {
        "id": "ICDR_REG_87",
        "name": "Post-Issue Monitoring Report",
        "description": "Lead manager must submit post-issue monitoring report to SEBI within 3 days of closure and allotment.",
    },
]


class ComplianceService:
    @staticmethod
    async def run_checks(
        db: AsyncSession, workspace_id: str
    ) -> list[ComplianceCheck]:
        checks: list[ComplianceCheck] = []
        for rule in SEBI_RULES:
            check = ComplianceCheck(
                workspace_id=workspace_id,
                check_type=rule["id"],
                regulation=rule["name"],
                status="pending",
                evidence={},
                ai_reasoning=None,
            )
            db.add(check)
            checks.append(check)
        await db.flush()
        for check in checks:
            await db.refresh(check)
        return checks

    @staticmethod
    async def get_checks(
        db: AsyncSession, workspace_id: str
    ) -> list[ComplianceCheck]:
        result = await db.execute(
            select(ComplianceCheck)
            .where(ComplianceCheck.workspace_id == workspace_id)
            .order_by(ComplianceCheck.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_check(db: AsyncSession, check_id: str) -> ComplianceCheck:
        result = await db.execute(
            select(ComplianceCheck).where(
                ComplianceCheck.id == check_id
            )
        )
        check = result.scalars().first()
        if check is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Compliance check not found",
            )
        return check

    @staticmethod
    async def update_check(
        db: AsyncSession,
        check_id: str,
        status_value: str,
        evidence: dict[str, Any],
        reasoning: str | None,
    ) -> ComplianceCheck:
        check = await ComplianceService.get_check(db, check_id)
        check.status = status_value  # type: ignore
        check.evidence = evidence  # type: ignore
        check.ai_reasoning = reasoning  # type: ignore
        db.add(check)
        await db.flush()
        await db.refresh(check)
        return check
