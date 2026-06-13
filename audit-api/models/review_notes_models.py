import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReviewNoteStatus(StrEnum):
    OPEN = "open"
    RESPONDED = "responded"
    CLEARED = "cleared"


class ReviewNoteCreate(BaseModel):
    text: str = Field(min_length=1)
    assigned_to: str | None = None
    working_paper_id: uuid.UUID | None = None


class ReviewNoteRespond(BaseModel):
    response: str = Field(min_length=1)


class ReviewNoteRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    working_paper_id: uuid.UUID | None
    text: str
    raised_by: str
    assigned_to: str | None
    status: str
    response: str | None
    responded_by: str | None
    responded_at: datetime | None
    cleared_by: str | None
    cleared_at: datetime | None
    created_at: datetime
