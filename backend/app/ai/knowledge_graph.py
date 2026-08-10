"""
Knowledge Graph Builder
Extracts and persists entities and relationships from the DRHP Request into the GraphEntity/GraphRelationship tables.
"""
from __future__ import annotations

import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.drhp_v2 import DrhpRequestV2
from app.models.enterprise import GraphEntity, GraphRelationship

logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    
    @staticmethod
    async def build_from_drhp(db: AsyncSession, workspace_id: str, req: DrhpRequestV2) -> None:
        """
        Parses a DrhpRequestV2 and populates the Knowledge Graph (GraphEntity and GraphRelationship).
        """
        logger.info("Building Knowledge Graph for workspace %s", workspace_id)
        
        # 1. Company Entity
        company_entity = GraphEntity(
            workspace_id=workspace_id,
            entity_type="Company",
            name=req.company.name,
            properties=json.dumps({"cin": req.company.cin, "pan": req.company.pan, "sector": req.company.sector})
        )
        db.add(company_entity)
        await db.flush() # To get ID
        
        # 2. Sector Entity
        sector_entity = GraphEntity(
            workspace_id=workspace_id,
            entity_type="Sector",
            name=req.company.sector,
            properties="{}"
        )
        db.add(sector_entity)
        await db.flush()
        
        # Company -> Sector
        db.add(GraphRelationship(
            workspace_id=workspace_id,
            source_entity_id=company_entity.id,
            target_entity_id=sector_entity.id,
            relationship_type="OPERATES_IN",
            properties="{}"
        ))
        
        # 3. Promoters
        if req.promoters:
            for p in req.promoters:
                promoter_entity = GraphEntity(
                    workspace_id=workspace_id,
                    entity_type="Promoter",
                    name=p.name,
                    properties=json.dumps({"type": "Individual" if "individual" in p.name.lower() else "Corporate"})
                )
                db.add(promoter_entity)
                await db.flush()
                
                db.add(GraphRelationship(
                    workspace_id=workspace_id,
                    source_entity_id=promoter_entity.id,
                    target_entity_id=company_entity.id,
                    relationship_type="PROMOTES",
                    properties=json.dumps({"holding_pct": p.holding_pct})
                ))
                
        # 4. Auditors
        if req.financials:
            auditors = {fy.auditor_name for fy in req.financials if fy.auditor_name}
            for auditor_name in auditors:
                auditor_entity = GraphEntity(
                    workspace_id=workspace_id,
                    entity_type="Auditor",
                    name=auditor_name,
                    properties="{}"
                )
                db.add(auditor_entity)
                await db.flush()
                
                db.add(GraphRelationship(
                    workspace_id=workspace_id,
                    source_entity_id=auditor_entity.id,
                    target_entity_id=company_entity.id,
                    relationship_type="AUDITS",
                    properties="{}"
                ))

        # 5. Directors/Management (Extracted from management structure if available, here mocked)
        if req.management:
            for m in req.management:
                director_entity = GraphEntity(
                    workspace_id=workspace_id,
                    entity_type="Director",
                    name=m.name,
                    properties=json.dumps({"designation": m.designation})
                )
                db.add(director_entity)
                await db.flush()
                
                db.add(GraphRelationship(
                    workspace_id=workspace_id,
                    source_entity_id=director_entity.id,
                    target_entity_id=company_entity.id,
                    relationship_type="DIRECTS",
                    properties="{}"
                ))

        await db.commit()
        logger.info("Knowledge Graph successfully populated for workspace %s", workspace_id)
