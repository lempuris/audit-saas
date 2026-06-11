import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EngagementType(StrEnum):
    AUDIT = "audit"
    REVIEW = "review"
    AGREED_UPON_PROCEDURES = "agreed_upon_procedures"
    OTHER = "other"


class EngagementStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    FIELDWORK = "fieldwork"
    REVIEW = "review"
    COMPLETED = "completed"


class EngagementCreate(BaseModel):
    client_id: uuid.UUID
    engagement_type: EngagementType
    fiscal_year: int = Field(ge=2000, le=2100)


class EngagementUpdate(BaseModel):
    engagement_type: EngagementType | None = None
    fiscal_year: int | None = Field(default=None, ge=2000, le=2100)


class StatusChangeRequest(BaseModel):
    status: EngagementStatus


class TeamMemberAdd(BaseModel):
    clerk_user_id: str
    role_on_engagement: str | None = None


class TeamMemberRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clerk_user_id: str
    role_on_engagement: str | None
    independence_confirmed: bool
    independence_confirmed_at: datetime | None


class EngagementRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    engagement_type: str
    fiscal_year: int
    status: str
    created_at: datetime
    updated_at: datetime


class EngagementDetail(EngagementRecord):
    team: list[TeamMemberRecord] = []
