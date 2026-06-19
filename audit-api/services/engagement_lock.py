"""Shared read-only lock for completed (archived) engagements.

When an engagement is completed it is archived and its whole file becomes
immutable (ISA 230 retention). Write services call require_open() after loading
the engagement to refuse mutations once it is completed. The core fieldwork and
planning services predate this helper and carry their own equivalent guard.
"""

from fastapi import HTTPException, status

from database.models import Engagement
from models.engagements_models import EngagementStatus


def require_open(engagement: Engagement) -> None:
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Engagement is completed and archived (read-only)",
        )
