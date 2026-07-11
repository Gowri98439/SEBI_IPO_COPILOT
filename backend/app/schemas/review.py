from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DraftReviewCreate(BaseModel):
    workspace_id: UUID
    section: str
    draft_content: str | None = None


class DraftReviewUpdate(BaseModel):
    status: str | None = None
    ai_feedback: list[Any] | None = None


class DraftReviewResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    section: str
    draft_content: str | None
    ai_feedback: list[Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewTaskCreate(BaseModel):
    workspace_id: UUID
    assigned_to: UUID | None = None
    task_type: str
    notes: str | None = None
    due_date: date | None = None


class ReviewTaskUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class ReviewTaskResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    assigned_to: UUID | None
    task_type: str
    status: str
    notes: str | None
    due_date: date | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
