"""
Cache models for IPO Copilot AI.
Implements compliance check caching and MD5-based embedding caching.
"""
import datetime
from typing import Any
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ComplianceCache(Base):
    __tablename__ = "compliance_cache"

    # Composite logic: we can hash the document content and the check_id
    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    document_hash: Mapped[str] = mapped_column(String(255), index=True)
    check_type: Mapped[str] = mapped_column(String(255), index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    # MD5 hash of the text chunk
    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    embedding: Mapped[dict[str, Any]] = mapped_column(JSON)  # stores list of floats
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
