import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, ForeignKey
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False)
    cin = Column(String, nullable=True)
    pan = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
