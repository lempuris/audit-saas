"""User management: reads from the local users mirror, writes through the
Clerk Backend API (the webhook keeps the mirror in sync; local rows are also
updated immediately so the UI reflects the change without waiting for the
webhook round trip). Every write lands in the audit trail.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from models.users_models import UserRecord
from services import audit_trail_service
from services.clerk_client import ClerkBackendClient


async def list_users(session: AsyncSession) -> list[UserRecord]:
    rows = await session.scalars(select(User).order_by(User.created_at))
    return [UserRecord.model_validate(row) for row in rows]


async def _get_user(session: AsyncSession, clerk_user_id: str) -> User:
    user = (await session.scalars(select(User).where(User.clerk_user_id == clerk_user_id))).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def invite_user(
    session: AsyncSession, clerk: ClerkBackendClient, *, actor: str, email: str, role: str
) -> None:
    await clerk.create_invitation(email, role)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type="invitation",
        entity_id=email,
        after={"email": email, "role": role},
    )
    await session.commit()


async def set_role(
    session: AsyncSession,
    clerk: ClerkBackendClient,
    *,
    actor: str,
    clerk_user_id: str,
    role: str,
) -> UserRecord:
    user = await _get_user(session, clerk_user_id)
    before = {"role": user.role}
    await clerk.set_user_role(clerk_user_id, role)
    user.role = role
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type="user",
        entity_id=clerk_user_id,
        before=before,
        after={"role": role},
    )
    await session.commit()
    return UserRecord.model_validate(user)


async def set_active(
    session: AsyncSession,
    clerk: ClerkBackendClient,
    *,
    actor: str,
    clerk_user_id: str,
    active: bool,
) -> UserRecord:
    user = await _get_user(session, clerk_user_id)
    before = {"is_active": user.is_active}
    if active:
        await clerk.unban_user(clerk_user_id)
    else:
        await clerk.ban_user(clerk_user_id)
    user.is_active = active
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type="user",
        entity_id=clerk_user_id,
        before=before,
        after={"is_active": active},
    )
    await session.commit()
    return UserRecord.model_validate(user)
