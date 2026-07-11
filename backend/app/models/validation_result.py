import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    issues = Column(JSON, nullable=True)
    missing_info = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    ai_model = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
