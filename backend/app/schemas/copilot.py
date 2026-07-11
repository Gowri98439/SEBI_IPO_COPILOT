from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    workspace_id: UUID


class SessionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str
    action_type: str | None = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    action_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
