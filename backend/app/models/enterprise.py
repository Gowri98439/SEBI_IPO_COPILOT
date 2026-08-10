import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

def _now():
    return datetime.now(timezone.utc)


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    regulation_id = Column(String, nullable=False, index=True) # e.g., "ICDR"
    version_tag = Column(String, nullable=False) # e.g., "2026-08"
    effective_date = Column(DateTime(timezone=True), nullable=True)
    superseded_date = Column(DateTime(timezone=True), nullable=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    
    # Traceability
    source_document_id = Column(String(36), nullable=True)
    document_version = Column(String, nullable=True)
    page_number = Column(String, nullable=True)
    section_name = Column(String, nullable=True)
    source_text = Column(Text, nullable=True)
    
    regulation_id = Column(String(36), ForeignKey("regulation_versions.id"), nullable=True)
    retrieval_score = Column(Float, nullable=True)
    ai_model = Column(String, nullable=True)
    
    # Status
    verification_status = Column(String, nullable=False, default="PENDING") # VERIFIED, PENDING, REJECTED, NOT_VERIFIED
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class ComplianceFinding(Base):
    __tablename__ = "compliance_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    
    rule_id = Column(String, nullable=False, index=True)
    regulation = Column(String, nullable=False)
    requirement = Column(Text, nullable=False)
    
    status = Column(String, nullable=False) # PASS, FAIL, PARTIAL, MISSING, NOT_APPLICABLE, REQUIRES_REVIEW
    evidence_id = Column(String(36), ForeignKey("evidence_records.id"), nullable=True)
    page = Column(String, nullable=True)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    
    regulation_version_id = Column(String(36), ForeignKey("regulation_versions.id"), nullable=True)
    review_requirement = Column(Boolean, default=True) # True if requires human sign-off
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    
    category = Column(String, nullable=False) # Financial, Regulatory, Legal, Governance, Business
    severity = Column(String, nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    
    evidence_id = Column(String(36), ForeignKey("evidence_records.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    target_type = Column(String, nullable=False) # e.g. "ComplianceFinding", "RiskFinding"
    target_id = Column(String(36), nullable=False)
    
    decision = Column(String, nullable=False) # APPROVED, REJECTED, MODIFIED
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    
    current_stage = Column(String, nullable=False, default="SUBMISSION") 
    # SUBMISSION, SCREENING, VALIDATION, AI_ANALYSIS, COMPLIANCE_REVIEW, RISK_REVIEW, HUMAN_REVIEW, CORRECTION, APPROVED
    
    assigned_officer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class HistoricalIPO(Base):
    __tablename__ = "historical_ipos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_name = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=True, index=True)
    exchange = Column(String, nullable=True)
    
    issue_size_cr = Column(Float, nullable=True)
    revenue_cr = Column(Float, nullable=True)
    pat_cr = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    
    subscription_times = Column(Float, nullable=True)
    listing_price = Column(Float, nullable=True)
    listing_performance_pct = Column(Float, nullable=True)
    
    promoters = Column(Text, nullable=True)
    auditor = Column(String, nullable=True)
    
    source = Column(String, nullable=True)
    source_date = Column(DateTime(timezone=True), nullable=True)
    
    verification_status = Column(String, nullable=False, default="SYNTHETIC") # SYNTHETIC vs VERIFIED
    last_verified_date = Column(DateTime(timezone=True), nullable=True)


class AIExecution(Base):
    __tablename__ = "ai_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    
    job_id = Column(String, nullable=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    
    tokens_prompt = Column(Float, nullable=True)
    tokens_completion = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


# ── Knowledge Graph Models ──────────────────────────────────────────────────

class GraphEntity(Base):
    __tablename__ = "graph_entities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    
    entity_type = Column(String, nullable=False, index=True) # Company, Promoter, Director, Auditor, Sector, Regulation, IPO, Risk
    name = Column(String, nullable=False, index=True)
    properties = Column(Text, nullable=True) # JSON representation of extra properties
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class GraphRelationship(Base):
    __tablename__ = "graph_relationships"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    
    source_entity_id = Column(String(36), ForeignKey("graph_entities.id"), nullable=False, index=True)
    target_entity_id = Column(String(36), ForeignKey("graph_entities.id"), nullable=False, index=True)
    
    relationship_type = Column(String, nullable=False, index=True) # e.g. "AUDITS", "DIRECTS", "OPERATES_IN", "REGULATED_BY"
    properties = Column(Text, nullable=True) # JSON representation of extra properties (e.g. from_date, to_date, holding_pct)
    
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

