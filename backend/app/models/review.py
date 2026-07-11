import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON, Date
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class DraftReview(Base):
    __tablename__ = "draft_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    section = Column(String, nullable=False)
    draft_content = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    ai_feedback = Column(JSON, nullable=True, default=[])
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    notes = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
