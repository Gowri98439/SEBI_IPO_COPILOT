from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ComplianceCheckResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    check_type: str
    regulation: str
    status: str
    evidence: dict[str, Any]
    ai_reasoning: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceRunRequest(BaseModel):
    workspace_id: str
