import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditTrailRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_clerk_user_id: str
    # Resolved from the users mirror; None when the actor is a system process
    # (e.g. the Clerk webhook) or an id with no matching user row.
    actor_name: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class AuditTrailPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditTrailRecord]
