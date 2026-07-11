from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    doc_type: str | None
    file_size: int | None
    mime_type: str | None
    status: str
    uploaded_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidationResultResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    issues: list[Any]
    missing_info: list[Any]
    summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
