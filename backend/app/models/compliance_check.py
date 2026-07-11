import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    check_type = Column(String, nullable=False)
    regulation = Column(String, nullable=False)
    status = Column(String, nullable=False)
    evidence = Column(JSON, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
