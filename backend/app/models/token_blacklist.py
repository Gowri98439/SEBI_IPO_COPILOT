import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, ForeignKey
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    jti = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), default=_now, nullable=False)
