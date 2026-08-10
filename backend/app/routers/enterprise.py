"""
Enterprise Intelligence API Routes
Exposes Readiness Score, Risk Profile, and Knowledge Graph.
"""
import uuid
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.enterprise import RiskFinding, GraphEntity, GraphRelationship, ComplianceFinding
from app.models.workspace import Workspace

router = APIRouter(prefix="/workspaces", tags=["Enterprise Intelligence"])

async def _verify_workspace(workspace_id: uuid.UUID, user: User, db: AsyncSession) -> Workspace:
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == str(workspace_id),
            Workspace.created_by == user.id,
        )
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.get("/{workspace_id}/intelligence/readiness")
async def get_readiness_score(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _verify_workspace(workspace_id, current_user, db)
    
    # Simple aggregation of readiness based on findings since DrhpRequestV2 isn't persisted here easily
    compliance_stmt = select(ComplianceFinding).where(ComplianceFinding.workspace_id == str(workspace_id))
    compliance_result = await db.execute(compliance_stmt)
    compliance_findings = compliance_result.scalars().all()
    
    risk_stmt = select(RiskFinding).where(RiskFinding.workspace_id == str(workspace_id))
    risk_result = await db.execute(risk_stmt)
    risk_findings = risk_result.scalars().all()
    
    reg_score = 100.0
    if compliance_findings:
        total_checks = len(compliance_findings)
        passed = sum(1 for c in compliance_findings if c.status == "pass")
        reg_score = (passed / total_checks) * 100

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
    
    overall_score = (reg_score * 0.6) + (risk_score * 0.4)
    if overall_score >= 85:
        band = "READY FOR FILING"
    elif overall_score >= 70:
        band = "REQUIRES REMEDIATION"
    else:
        band = "NOT READY"
        
    return {
        "overall_score": round(overall_score, 1),
        "readiness_band": band,
        "component_scores": {
            "regulatory_readiness": round(reg_score, 1),
            "risk_profile": round(risk_score, 1),
        },
        "critical_blockers": [r.description for r in risk_findings if r.severity in ("CRITICAL", "HIGH")]
    }

@router.get("/{workspace_id}/intelligence/risks")
async def get_risk_profile(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    await _verify_workspace(workspace_id, current_user, db)
    stmt = select(RiskFinding).where(RiskFinding.workspace_id == str(workspace_id))
    result = await db.execute(stmt)
    findings = result.scalars().all()
    return [{"id": f.id, "category": f.category, "severity": f.severity, "description": f.description} for f in findings]

@router.get("/{workspace_id}/intelligence/graph")
async def get_knowledge_graph(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _verify_workspace(workspace_id, current_user, db)
    
    estmt = select(GraphEntity).where(GraphEntity.workspace_id == str(workspace_id))
    eresult = await db.execute(estmt)
    entities = eresult.scalars().all()
    
    rstmt = select(GraphRelationship).where(GraphRelationship.workspace_id == str(workspace_id))
    rresult = await db.execute(rstmt)
    relationships = rresult.scalars().all()
    
    return {
        "nodes": [{"id": e.id, "label": e.name, "type": e.entity_type, "properties": e.properties} for e in entities],
        "links": [{"source": r.source_entity_id, "target": r.target_entity_id, "type": r.relationship_type, "properties": r.properties} for r in relationships]
    }
