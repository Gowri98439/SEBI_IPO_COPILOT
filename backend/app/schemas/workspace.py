from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    company_id: UUID
    name: str


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
