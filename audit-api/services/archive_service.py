"""Engagement archive & retention (ISA 230). When an engagement is completed,
engagements_service stages an archive record here (atomically, within the same
transaction as the status change) marking who archived it, when, and the
retention period. The whole file is then read-only — enforced by the per-service
completion guards and engagement_lock.require_open.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import EngagementArchive, User
from models.archive_models import ArchiveRecord
from services import audit_trail_service
from utils.naming import display_name

ENTITY_TYPE = "engagement_archive"

# ISA 230 requires retention of at least five years from the auditor's report
# date; the firm policy here is seven.
DEFAULT_RETENTION_YEARS = 7


def _retention_until(archived_at: datetime, years: int) -> datetime:
    try:
        return archived_at.replace(year=archived_at.year + years)
    except ValueError:
        # 29 Feb in a leap year -> fall back to the 28th.
        return archived_at.replace(year=archived_at.year + years, day=28)


async def _get(session: AsyncSession, engagement_id: uuid.UUID) -> EngagementArchive | None:
    rows = await session.scalars(
        select(EngagementArchive).where(EngagementArchive.engagement_id == engagement_id)
    )
    return next((a for a in rows if a.engagement_id == engagement_id), None)


async def archive_on_completion(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    retention_years: int = DEFAULT_RETENTION_YEARS,
) -> None:
    """Stage the archive record + audit row (no commit — the caller's status
    change commits them atomically). Idempotent: a no-op if already archived."""
    if await _get(session, engagement_id) is not None:
        return
    now = datetime.now(UTC)
    archive = EngagementArchive(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        archived_by=actor,
        archived_at=now,
        retention_years=retention_years,
        retention_until=_retention_until(now, retention_years),
    )
    session.add(archive)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(engagement_id),
        after={
            "retention_years": retention_years,
            "retention_until": archive.retention_until.isoformat(),
        },
    )


async def get_archive(session: AsyncSession, engagement_id: uuid.UUID) -> ArchiveRecord | None:
    archive = await _get(session, engagement_id)
    if archive is None:
        return None
    record = ArchiveRecord.model_validate(archive)
    user = (
        await session.scalars(select(User).where(User.clerk_user_id == archive.archived_by))
    ).first()
    if user is not None:
        record.archived_by_name = display_name(user.first_name, user.last_name, user.email)
    return record
