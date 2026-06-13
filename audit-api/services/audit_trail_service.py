"""Audit trail: every create/update/delete on business data and every login
gets an immutable row. Services call record() inside their own transaction so
the audit row commits atomically with the write it describes.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditTrailEntry, User
from models.audit_trail_models import AuditTrailPage, AuditTrailRecord
from utils.naming import display_name

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
    rows = list(
        await session.scalars(
            query.order_by(AuditTrailEntry.created_at.desc()).limit(limit).offset(offset)
        )
    )

    # Resolve actor ids to names/emails so the viewer shows people, not opaque
    # Clerk ids. System actors (the webhook) have no user row and stay raw.
    actor_ids = {row.actor_clerk_user_id for row in rows}
    users = (await session.scalars(select(User).where(User.clerk_user_id.in_(actor_ids)))).all()
    by_id = {user.clerk_user_id: user for user in users}

    items = []
    for row in rows:
        record = AuditTrailRecord.model_validate(row)
        user = by_id.get(row.actor_clerk_user_id)
        if user is not None:
            record.actor_name = display_name(user.first_name, user.last_name, user.email)
            record.actor_email = user.email
        items.append(record)

    return AuditTrailPage(total=total or 0, limit=limit, offset=offset, items=items)
