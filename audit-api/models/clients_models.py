import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RiskRating(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClientContact(BaseModel):
    name: str
    position: str | None = None
    email: str | None = None
    phone: str | None = None


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    industry: str | None = None
    risk_rating: RiskRating | None = None
    contacts: list[ClientContact] = []


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    industry: str | None = None
    risk_rating: RiskRating | None = None
    contacts: list[ClientContact] | None = None


class ClientRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    risk_rating: str | None
    contacts: list[ClientContact]
    archived: bool
    created_at: datetime
    updated_at: datetime
