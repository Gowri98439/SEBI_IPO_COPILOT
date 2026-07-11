import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action_category = Column(String, nullable=False, default="DOCUMENT")
    action = Column(String, nullable=False)
    target_id = Column(String(36), nullable=True)
    target_type = Column(String, nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String, nullable=True, default="success")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)
