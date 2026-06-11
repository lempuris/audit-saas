"""Audit trail: every create/update/delete on business data and every login
gets an immutable row. Services call record() inside their own transaction so
the audit row commits atomically with the write it describes.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditTrailEntry
from models.audit_trail_models import AuditTrailPage, AuditTrailRecord

# Actor recorded for rows written by webhook sync rather than a request.
SYSTEM_ACTOR = "system:clerk-webhook"


def record(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditTrailEntry:
    """Stage an audit row in the caller's transaction (no commit here)."""
    entry = AuditTrailEntry(
        actor_clerk_user_id=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
    )
    session.add(entry)
    return entry


async def list_entries(
    session: AsyncSession,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditTrailPage:
    query = select(AuditTrailEntry)
    if entity_type:
        query = query.where(AuditTrailEntry.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditTrailEntry.entity_id == entity_id)
    if actor:
        query = query.where(AuditTrailEntry.actor_clerk_user_id == actor)

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.scalars(
        query.order_by(AuditTrailEntry.created_at.desc()).limit(limit).offset(offset)
    )
    return AuditTrailPage(
        total=total or 0,
        limit=limit,
        offset=offset,
        items=[AuditTrailRecord.model_validate(row) for row in rows],
    )
