import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Integer, Text, JSON
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class CorpusVersion(Base):
    __tablename__ = "corpus_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    version = Column(String, nullable=False)
    embedding_model = Column(String, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    chunk_overlap = Column(Integer, nullable=False)
    chunking_strategy = Column(String, nullable=False)
    regulations = Column(JSON, nullable=False)
    drhp_count = Column(Integer, default=0)
    built_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    notes = Column(Text, nullable=True)
