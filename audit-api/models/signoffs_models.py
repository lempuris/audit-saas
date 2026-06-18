import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SignoffTargetType(StrEnum):
    WORKING_PAPER = "working_paper"
    FS_AREA = "fs_area"


class SignoffAction(StrEnum):
    """Caller-requested transition. The stored event is the past-tense result
    (review -> reviewed, approve -> approved, return -> returned)."""

    REVIEW = "review"
    APPROVE = "approve"
    RETURN = "return"


class SignoffRequest(BaseModel):
    action: SignoffAction
    note: str | None = None


class SignoffRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    target_type: str
    target_id: str
    action: str  # reviewed / approved / returned
    resulting_status: str
    signed_by: str
    note: str | None
    created_at: datetime
    # Resolved display name for signed_by (Clerk id otherwise); set by service.
    signed_by_name: str | None = None
