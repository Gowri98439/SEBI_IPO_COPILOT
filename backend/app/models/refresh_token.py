import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
