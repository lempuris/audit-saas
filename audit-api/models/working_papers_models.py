import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.trial_balance_models import FSArea


class WorkingPaperStatus(StrEnum):
    """Full working-paper lifecycle. draft<->prepared are set via the status
    endpoint; reviewed/approved are reached only through the sign-off workflow
    (signoffs_service), which also returns an approved/reviewed paper to
    prepared."""

    DRAFT = "draft"
    PREPARED = "prepared"
    REVIEWED = "reviewed"
    APPROVED = "approved"


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

    @field_validator("status")
    @classmethod
    def _only_preparation(cls, value: WorkingPaperStatus) -> WorkingPaperStatus:
        # reviewed/approved are reached only via the sign-off endpoint.
        if value not in (WorkingPaperStatus.DRAFT, WorkingPaperStatus.PREPARED):
            raise ValueError("Use the sign-off endpoint to review or approve a working paper")
        return value


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
    # Resolved display name for prepared_by (Clerk id otherwise); set by service.
    prepared_by_name: str | None = None


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
    # Resolved display name for edited_by (Clerk id otherwise); set by service.
    edited_by_name: str | None = None
