"""
Evidence Engine for the IPO Copilot platform.
Ensures every AI-generated conclusion, compliance finding, or risk is anchored to an EvidenceRecord.
"""
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.enterprise import EvidenceRecord

logger = logging.getLogger(__name__)

class EvidenceEngine:
    """
    Manages the lifecycle and provenance of AI-generated evidence records.
    Every major AI conclusion must be supported by an EvidenceRecord.
    """
    
    @staticmethod
    async def generate_evidence(
        db: AsyncSession,
        workspace_id: str,
        claim_text: str,
        source_text: str | None = None,
        source_document_id: str | None = None,
        document_version: str | None = None,
        page_number: str | None = None,
        section_name: str | None = None,
        regulation_id: str | None = None,
        retrieval_score: float | None = None,
        ai_model: str | None = None,
        is_synthetic: bool = False
    ) -> EvidenceRecord:
        """
        Creates and persists an EvidenceRecord for an AI claim.
        If is_synthetic is True (e.g. historical dummy data), verification_status is SYNTHETIC.
        Otherwise, it defaults to PENDING for human review.
        """
        status = "SYNTHETIC" if is_synthetic else "PENDING"
        
        # If no source_text is provided, we can't truly verify it.
        if not source_text and not is_synthetic:
            status = "NOT_VERIFIED"
            
        record = EvidenceRecord(
            workspace_id=workspace_id,
            claim_text=claim_text,
            source_text=source_text,
            source_document_id=source_document_id,
            document_version=document_version,
            page_number=page_number,
            section_name=section_name,
            regulation_id=regulation_id,
            retrieval_score=retrieval_score,
            ai_model=ai_model,
            verification_status=status
        )
        
        db.add(record)
        await db.flush()
        await db.refresh(record)
        
        logger.debug("Generated EvidenceRecord: %s (Status: %s) for workspace %s", record.id, status, workspace_id)
        return record
        
    @staticmethod
    async def review_evidence(
        db: AsyncSession,
        evidence_id: str,
        reviewer_id: str,
        action: str  # 'VERIFY', 'REJECT'
    ) -> EvidenceRecord | None:
        """
        Allows a human reviewer to verify or reject an AI evidence record.
        """
        result = await db.execute(
            select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
        )
        record = result.scalars().first()
        
        if not record:
            return None
            
        if action == "VERIFY":
            record.verification_status = "VERIFIED"
        elif action == "REJECT":
            record.verification_status = "REJECTED"
        else:
            raise ValueError(f"Invalid evidence review action: {action}")
            
        record.reviewer_id = reviewer_id
        db.add(record)
        await db.flush()
        
        logger.info("EvidenceRecord %s was %s by user %s", evidence_id, action, reviewer_id)
        return record

    @staticmethod
    async def get_workspace_evidence(
        db: AsyncSession,
        workspace_id: str,
        status_filter: str | None = None
    ) -> list[EvidenceRecord]:
        """
        Retrieve all evidence records for a workspace, optionally filtered by status.
        """
        stmt = select(EvidenceRecord).where(EvidenceRecord.workspace_id == workspace_id)
        if status_filter:
            stmt = stmt.where(EvidenceRecord.verification_status == status_filter)
            
        result = await db.execute(stmt)
        return list(result.scalars().all())

