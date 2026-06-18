import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArchiveRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    archived_by: str
    archived_at: datetime
    retention_years: int
    retention_until: datetime
    note: str | None
    created_at: datetime
    # Resolved display name for archived_by (Clerk id otherwise); set by service.
    archived_by_name: str | None = None
