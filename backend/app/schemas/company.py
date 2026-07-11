from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    cin: str | None = None
    pan: str | None = None
    industry: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    pan: str | None = None
    industry: str | None = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    cin: str | None
    pan: str | None
    industry: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
