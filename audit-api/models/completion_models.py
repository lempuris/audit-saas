import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ChecklistItemStatus(StrEnum):
    OPEN = "open"
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"


# Statuses that count as resolved for the completion gate.
RESOLVED_STATUSES = frozenset({ChecklistItemStatus.COMPLETE, ChecklistItemStatus.NOT_APPLICABLE})


class ChecklistItemUpdate(BaseModel):
    status: ChecklistItemStatus
    note: str | None = None


class ChecklistItemRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    item_key: str
    category: str
    title: str
    isa_reference: str | None
    status: str
    note: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    # Resolved display name for resolved_by (Clerk id otherwise); set by service.
    resolved_by_name: str | None = None


class CompletionReadiness(BaseModel):
    """Whether an engagement can close, with the blocking counts for the UI."""

    ready: bool
    total_items: int
    open_items: int
    uncleared_notes: int
