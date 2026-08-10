"""
Risk Intelligence Engine
Detects Financial, Regulatory, Legal, Governance, and Business risks.
Generates structured RiskFinding records.
"""
from __future__ import annotations

import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.drhp_v2 import DrhpRequestV2
from app.models.enterprise import RiskFinding
from app.ai.evidence_engine import EvidenceEngine

logger = logging.getLogger(__name__)

class RiskEngine:
    
    @staticmethod
    async def analyze_risks(db: AsyncSession, workspace_id: str, req: DrhpRequestV2) -> List[RiskFinding]:
        """
        Analyze the DRHP data and return a list of identified risks.
        Persists them as RiskFinding to the database.
        """
        risks = []
        
        # 1. Financial Risk - High Leverage
        if req.financials:
            latest_fy = req.financials[-1]
            if latest_fy.total_debt is not None and latest_fy.total_equity and latest_fy.total_equity > 0:
                debt_equity = latest_fy.total_debt / latest_fy.total_equity
                if debt_equity > 2.0:
                    risks.append({
                        "risk_type": "Financial",
                        "severity": "HIGH",
                        "description": f"High Debt-to-Equity Ratio ({debt_equity:.2f}x) in latest financial year.",
                        "mitigation_strategy": "Disclose strategy to reduce debt post-IPO.",
                        "evidence_claim": f"Total Debt is {latest_fy.total_debt} and Equity is {latest_fy.total_equity}."
                    })
                    
            # 2. Financial Risk - Negative Operating Cash Flow
            if latest_fy.operating_cash_flow is not None and latest_fy.operating_cash_flow < 0:
                risks.append({
                    "risk_type": "Financial",
                    "severity": "MEDIUM",
                    "description": f"Negative Operating Cash Flow (₹{latest_fy.operating_cash_flow} Lakhs) in {latest_fy.year}.",
                    "mitigation_strategy": "Explain cash burn rate and funding runway.",
                    "evidence_claim": f"OCF is {latest_fy.operating_cash_flow}."
                })
        
        # 3. Legal Risk - Material Litigation
        if req.legal_proceedings:
            for lp in req.legal_proceedings:
                if lp.amount_involved_lakhs is not None and lp.amount_involved_lakhs > 1000:
                    risks.append({
                        "risk_type": "Legal",
                        "severity": "HIGH",
                        "description": f"Material litigation involving ₹{lp.amount_involved_lakhs} Lakhs before {lp.court_or_tribunal}.",
                        "mitigation_strategy": "Provide detailed legal opinion on the likely outcome.",
                        "evidence_claim": f"Litigation amount: {lp.amount_involved_lakhs}"
                    })
                    
        # 4. Governance Risk - Missing Auditor
        if req.financials:
            auditors = set([fy.auditor_name for fy in req.financials if fy.auditor_name])
            if not auditors:
                risks.append({
                    "risk_type": "Governance",
                    "severity": "CRITICAL",
                    "description": "No auditor information provided for financial statements.",
                    "mitigation_strategy": "Upload restated financial statements with auditor details.",
                    "evidence_claim": "auditor_name is null for all years."
                })
                
        # 5. Business Risk - High Customer Concentration (Mock logic based on products)
        if req.company.key_products:
            for p in req.company.key_products:
                if p.revenue_contribution_pct and p.revenue_contribution_pct > 50:
                    risks.append({
                        "risk_type": "Business",
                        "severity": "MEDIUM",
                        "description": f"High revenue concentration: {p.name} contributes {p.revenue_contribution_pct}% of revenue.",
                        "mitigation_strategy": "Disclose strategy for product/service diversification.",
                        "evidence_claim": f"Product {p.name} contribution is {p.revenue_contribution_pct}%."
                    })

        persisted_risks = []
        for risk in risks:
            # Generate evidence record for each risk
            evidence = await EvidenceEngine.generate_evidence(
                db=db,
                workspace_id=workspace_id,
                claim_text=risk["description"],
                source_text=risk["evidence_claim"],
                ai_model="risk-engine-v1",
                is_synthetic=False
            )
            
            finding = RiskFinding(
                workspace_id=workspace_id,
                risk_type=risk["risk_type"],
                severity=risk["severity"],
                description=risk["description"],
                mitigation_strategy=risk["mitigation_strategy"],
                evidence_id=evidence.id,
                status="OPEN"
            )
            db.add(finding)
            persisted_risks.append(finding)
            
        await db.commit()
        logger.info("RiskEngine identified %d risks for workspace %s", len(persisted_risks), workspace_id)
        return persisted_risks
