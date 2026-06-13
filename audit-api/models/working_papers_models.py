import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from models.trial_balance_models import FSArea


class WorkingPaperStatus(StrEnum):
    """Preparation status. The reviewed/approved sign-off workflow is Phase 4."""

    DRAFT = "draft"
    PREPARED = "prepared"


class WorkingPaperCreate(BaseModel):
    fs_area: FSArea
    index_ref: str = Field(min_length=1)
    title: str = Field(min_length=1)
    # Result/conclusion are typically filled in as fieldwork progresses, so a
    # draft can be created with just an objective.
    objective: str = ""
    result: str = ""
    conclusion: str = ""
    procedure_id: uuid.UUID | None = None


class WorkingPaperUpdate(BaseModel):
    fs_area: FSArea | None = None
    index_ref: str | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, min_length=1)
    objective: str | None = None
    result: str | None = None
    conclusion: str | None = None
    procedure_id: uuid.UUID | None = None


class WorkingPaperStatusUpdate(BaseModel):
    status: WorkingPaperStatus


class WorkingPaperRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    fs_area: str
    index_ref: str
    title: str
    objective: str
    result: str
    conclusion: str
    status: str
    procedure_id: uuid.UUID | None
    prepared_by: str | None
    prepared_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    # Highest version_no recorded; set by the service.
    current_version: int = 0


class WorkingPaperVersionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    working_paper_id: uuid.UUID
    version_no: int
    index_ref: str
    fs_area: str
    title: str
    objective: str
    result: str
    conclusion: str
    status: str
    edited_by: str
    created_at: datetime
