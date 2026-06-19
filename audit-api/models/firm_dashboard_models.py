import uuid
from datetime import date, datetime

from pydantic import BaseModel


class EngagementStatusBreakdown(BaseModel):
    """Every engagement counted by workflow status, plus the grand total."""

    by_status: dict[str, int]
    total: int


class ReviewQueueItem(BaseModel):
    """A working paper awaiting a sign-off action: prepared (needs a reviewer)
    or reviewed (needs partner approval)."""

    working_paper_id: uuid.UUID
    engagement_id: uuid.UUID
    client_name: str | None
    fiscal_year: int
    fs_area: str
    index_ref: str
    title: str
    status: str
    prepared_at: datetime | None
    prepared_by_name: str | None


class OverdueProcedure(BaseModel):
    """A still-open program procedure whose due date has passed."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    client_name: str | None
    fiscal_year: int
    fs_area: str
    title: str
    isa_reference: str | None
    status: str
    due_date: date
    days_overdue: int
    assignee_name: str | None


class FirmDashboard(BaseModel):
    """Firm-wide oversight: engagements by status, the sign-off review queue,
    overdue procedures, and the count of uncleared review notes. The work
    queues exclude completed (archived) engagements; the status breakdown
    counts every engagement."""

    engagements: EngagementStatusBreakdown
    review_queue: list[ReviewQueueItem]
    overdue_procedures: list[OverdueProcedure]
    open_review_notes: int
