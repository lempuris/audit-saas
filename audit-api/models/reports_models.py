import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportType(StrEnum):
    AUDIT_REPORT = "audit_report"
    MANAGEMENT_LETTER = "management_letter"


class OpinionType(StrEnum):
    UNMODIFIED = "unmodified"
    QUALIFIED = "qualified"
    ADVERSE = "adverse"
    DISCLAIMER = "disclaimer"


class ReportStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class ReportSection(BaseModel):
    key: str = Field(min_length=1)
    heading: str
    body: str


class ReportCreate(BaseModel):
    report_type: ReportType
    # Required for an audit report; must be omitted for a management letter.
    opinion_type: OpinionType | None = None

    @model_validator(mode="after")
    def _check_opinion(self) -> "ReportCreate":
        if self.report_type == ReportType.AUDIT_REPORT and self.opinion_type is None:
            raise ValueError("opinion_type is required for an audit report")
        if self.report_type == ReportType.MANAGEMENT_LETTER and self.opinion_type is not None:
            raise ValueError("opinion_type does not apply to a management letter")
        return self


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    letterhead: str | None = None
    status: ReportStatus | None = None
    sections: list[ReportSection] | None = None


class ReportRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    report_type: str
    opinion_type: str | None
    title: str
    letterhead: str
    sections: list[ReportSection]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
