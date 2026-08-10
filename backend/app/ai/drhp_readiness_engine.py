"""
IPO Readiness Engine
Aggregates Financial, Regulatory, Disclosure, Evidence, Legal, Governance, Risk, and Consistency scores.
Provides an AI-Assisted IPO Readiness Assessment.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.drhp_v2 import DrhpRequestV2, FinancialIntelligenceReport, ConsistencyReport
from app.models.enterprise import ComplianceFinding, RiskFinding

logger = logging.getLogger(__name__)

class IPOReadinessEngine:
    
    @staticmethod
    async def compute_readiness(
        db: AsyncSession,
        workspace_id: str,
        req: DrhpRequestV2,
        financial_report: FinancialIntelligenceReport,
        consistency_report: ConsistencyReport
    ) -> Dict[str, Any]:
        """
        Computes the overall IPO Readiness Score based on all intelligence engines.
        """
        logger.info("Computing IPO Readiness for workspace %s", workspace_id)
        
        # 1. Financial Readiness Score (0-100)
        # Based on data quality, altman Z, and profitability
        fin_score = financial_report.data_quality_score * 40
        fin_score += financial_report.financial_consistency_score * 30
        if financial_report.quality_scores.get("altman_z", {}).get("flag") == "green":
            fin_score += 20
        elif financial_report.quality_scores.get("altman_z", {}).get("flag") == "amber":
            fin_score += 10
            
        if not financial_report.red_flags:
            fin_score += 10
            
        fin_score = min(100, max(0, fin_score))
        
        # 2. Regulatory Readiness Score (0-100)
        compliance_stmt = select(ComplianceFinding).where(ComplianceFinding.workspace_id == workspace_id)
        compliance_result = await db.execute(compliance_stmt)
        compliance_findings = compliance_result.scalars().all()
        
        if compliance_findings:
            total_checks = len(compliance_findings)
            passed = sum(1 for c in compliance_findings if c.status == "pass")
            reg_score = (passed / total_checks) * 100
        else:
            reg_score = 0.0
            
        # 3. Risk Profile Score (0-100)
        risk_stmt = select(RiskFinding).where(RiskFinding.workspace_id == workspace_id)
        risk_result = await db.execute(risk_stmt)
        risk_findings = risk_result.scalars().all()
        
        risk_score = 100.0
        for r in risk_findings:
            if r.severity == "CRITICAL":
                risk_score -= 30
            elif r.severity == "HIGH":
                risk_score -= 20
            elif r.severity == "MEDIUM":
                risk_score -= 10
            elif r.severity == "LOW":
                risk_score -= 5
                
        risk_score = max(0.0, risk_score)
        
        # 4. Consistency Readiness Score (0-100)
        if consistency_report.status == "pass":
            cons_score = 100.0
        elif consistency_report.status == "warnings":
            cons_score = 75.0
        else:
            cons_score = 30.0
            
        # Overall Readiness Score (Weighted Average)
        overall_score = (
            (fin_score * 0.3) +
            (reg_score * 0.4) +
            (risk_score * 0.2) +
            (cons_score * 0.1)
        )
        
        # Assessment Band
        if overall_score >= 85 and reg_score >= 90 and risk_score >= 80:
            band = "READY FOR FILING"
        elif overall_score >= 70:
            band = "REQUIRES REMEDIATION"
        else:
            band = "NOT READY"
            
        return {
            "overall_score": round(overall_score, 1),
            "readiness_band": band,
            "component_scores": {
                "financial_readiness": round(fin_score, 1),
                "regulatory_readiness": round(reg_score, 1),
                "risk_profile": round(risk_score, 1),
                "document_consistency": round(cons_score, 1)
            },
            "critical_blockers": [r.description for r in risk_findings if r.severity in ("CRITICAL", "HIGH")]
        }
