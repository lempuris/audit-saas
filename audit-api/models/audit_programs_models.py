import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.risks_models import Assertion
from models.trial_balance_models import FSArea


class ProcedureStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


class TemplateCreate(BaseModel):
    fs_area: FSArea
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    isa_reference: str | None = None
    assertions: list[Assertion] = []
    sort_order: int = 0


class TemplateRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fs_area: str
    title: str
    description: str
    isa_reference: str | None
    assertions: list[str]
    sort_order: int


class SeedResult(BaseModel):
    created: int
    skipped: int


class ProcedureCreate(BaseModel):
    """Add one procedure: either from a template (fields copied, overridable)
    or fully custom (fs_area/title/description required)."""

    template_id: uuid.UUID | None = None
    fs_area: FSArea | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    isa_reference: str | None = None
    assertions: list[Assertion] | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def _custom_needs_fields(self) -> "ProcedureCreate":
        if self.template_id is None and not (self.fs_area and self.title and self.description):
            raise ValueError("Provide a template_id or all of fs_area, title and description")
        return self


class ProceduresFromTemplates(BaseModel):
    """Bulk-add templates to an engagement program — the whole library, one
    FS area, or an explicit list."""

    fs_area: FSArea | None = None
    template_ids: list[uuid.UUID] | None = None


class ProcedureUpdate(BaseModel):
    fs_area: FSArea | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    isa_reference: str | None = None
    assertions: list[Assertion] | None = None
    assigned_to: str | None = None
    status: ProcedureStatus | None = None
    due_date: date | None = None
    sort_order: int | None = None


class ProcedureStatusUpdate(BaseModel):
    status: ProcedureStatus


class RiskLinksUpdate(BaseModel):
    """Replaces the set of risks a procedure responds to."""

    risk_ids: list[uuid.UUID]


class ProcedureRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    template_id: uuid.UUID | None
    fs_area: str
    title: str
    description: str
    isa_reference: str | None
    assertions: list[str]
    assigned_to: str | None
    status: str
    due_date: date | None
    sort_order: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    linked_risk_ids: list[uuid.UUID] = []
