import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class CrossRefType(StrEnum):
    WORKING_PAPER = "working_paper"
    TRIAL_BALANCE_LINE = "trial_balance_line"
    DOCUMENT = "document"


class CrossReferenceCreate(BaseModel):
    source_type: CrossRefType
    source_id: uuid.UUID
    target_type: CrossRefType
    target_id: uuid.UUID
    label: str | None = None

    @model_validator(mode="after")
    def _no_self_reference(self) -> "CrossReferenceCreate":
        if self.source_type == self.target_type and self.source_id == self.target_id:
            raise ValueError("A cross-reference cannot link an item to itself")
        return self


class CrossReferenceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    label: str | None
    created_by: str
    created_at: datetime
    # Human-readable labels for each side, resolved by the service.
    source_label: str = ""
    target_label: str = ""
