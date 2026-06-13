"""Engagements: creation, status workflow, team assignment, and the
independence/conflict confirmation gate.

Workflow: draft -> planning -> fieldwork -> review -> completed, with
review -> fieldwork allowed for rework. Moving into fieldwork requires every
team member to have confirmed independence; completing requires Partner or
Admin. Every write lands in the audit trail.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Client, Engagement, EngagementTeamMember, User
from models.auth_models import AuthenticatedUser, Role
from models.engagements_models import (
    EngagementCreate,
    EngagementDetail,
    EngagementRecord,
    EngagementStatus,
    EngagementUpdate,
    StatusChangeRequest,
    TeamMemberAdd,
    TeamMemberRecord,
)
from services import audit_trail_service
from utils.naming import display_name

ENTITY_TYPE = "engagement"

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    EngagementStatus.DRAFT: {EngagementStatus.PLANNING},
    EngagementStatus.PLANNING: {EngagementStatus.FIELDWORK},
    EngagementStatus.FIELDWORK: {EngagementStatus.REVIEW},
    EngagementStatus.REVIEW: {EngagementStatus.FIELDWORK, EngagementStatus.COMPLETED},
    EngagementStatus.COMPLETED: set(),
}


def _snapshot(engagement: Engagement) -> dict:
    return {
        "client_id": str(engagement.client_id),
        "engagement_type": engagement.engagement_type,
        "fiscal_year": engagement.fiscal_year,
        "status": engagement.status,
    }


async def _get(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _team(session: AsyncSession, engagement_id: uuid.UUID) -> list[EngagementTeamMember]:
    rows = await session.scalars(
        select(EngagementTeamMember).where(EngagementTeamMember.engagement_id == engagement_id)
    )
    return list(rows)


async def list_engagements(
    session: AsyncSession,
    *,
    client_id: uuid.UUID | None = None,
    engagement_status: str | None = None,
) -> list[EngagementRecord]:
    query = select(Engagement).order_by(Engagement.fiscal_year.desc())
    if client_id:
        query = query.where(Engagement.client_id == client_id)
    if engagement_status:
        query = query.where(Engagement.status == engagement_status)
    rows = await session.scalars(query)
    return [EngagementRecord.model_validate(row) for row in rows]


async def get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> EngagementDetail:
    engagement = await _get(session, engagement_id)
    team = await _team(session, engagement_id)
    detail = EngagementDetail.model_validate(engagement)
    detail.team = await _team_records(session, team)
    return detail


async def _team_records(
    session: AsyncSession, team: list[EngagementTeamMember]
) -> list[TeamMemberRecord]:
    """Map team rows to records, resolving names/emails from the users mirror so
    the UI (e.g. the procedure-assignee dropdown) shows people, not Clerk ids."""
    member_ids = {member.clerk_user_id for member in team}
    users = list(await session.scalars(select(User).where(User.clerk_user_id.in_(member_ids))))
    by_id = {user.clerk_user_id: user for user in users}

    records = []
    for member in team:
        record = TeamMemberRecord.model_validate(member)
        user = by_id.get(member.clerk_user_id)
        if user is not None:
            record.display_name = display_name(user.first_name, user.last_name, user.email)
            record.email = user.email
        records.append(record)
    return records


async def create_engagement(
    session: AsyncSession, *, actor: str, payload: EngagementCreate
) -> EngagementRecord:
    client = (await session.scalars(select(Client).where(Client.id == payload.client_id))).first()
    if client is None or client.archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found or archived"
        )

    engagement = Engagement(
        id=uuid.uuid4(),
        client_id=payload.client_id,
        engagement_type=payload.engagement_type,
        fiscal_year=payload.fiscal_year,
        status=EngagementStatus.DRAFT,
    )
    session.add(engagement)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(engagement.id),
        after=_snapshot(engagement),
    )
    await session.commit()
    await session.refresh(engagement)
    return EngagementRecord.model_validate(engagement)


async def update_engagement(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: EngagementUpdate
) -> EngagementRecord:
    engagement = await _get(session, engagement_id)
    before = _snapshot(engagement)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(engagement, field, value)
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(engagement_id),
        before=before,
        after=_snapshot(engagement),
    )
    await session.commit()
    await session.refresh(engagement)
    return EngagementRecord.model_validate(engagement)


async def change_status(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    engagement_id: uuid.UUID,
    payload: StatusChangeRequest,
) -> EngagementRecord:
    engagement = await _get(session, engagement_id)
    current = engagement.status
    target = payload.status

    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot move engagement from '{current}' to '{target}'",
        )

    if target == EngagementStatus.COMPLETED and user.role not in (Role.ADMIN, Role.PARTNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a Partner or Admin can complete an engagement",
        )

    if target == EngagementStatus.FIELDWORK and current == EngagementStatus.PLANNING:
        team = await _team(session, engagement_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot start fieldwork without a team assigned",
            )
        unconfirmed = [m.clerk_user_id for m in team if not m.independence_confirmed]
        if unconfirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="All team members must confirm independence before fieldwork: "
                + ", ".join(unconfirmed),
            )

    before = _snapshot(engagement)
    engagement.status = target
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(engagement_id),
        before=before,
        after=_snapshot(engagement),
    )
    await session.commit()
    await session.refresh(engagement)
    return EngagementRecord.model_validate(engagement)


async def add_team_member(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: TeamMemberAdd
) -> TeamMemberRecord:
    await _get(session, engagement_id)
    team = await _team(session, engagement_id)
    if any(member.clerk_user_id == payload.clerk_user_id for member in team):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already on the team"
        )

    member = EngagementTeamMember(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        clerk_user_id=payload.clerk_user_id,
        role_on_engagement=payload.role_on_engagement,
        independence_confirmed=False,
    )
    session.add(member)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type="engagement_team_member",
        entity_id=f"{engagement_id}:{payload.clerk_user_id}",
        after={
            "engagement_id": str(engagement_id),
            "clerk_user_id": payload.clerk_user_id,
            "role_on_engagement": payload.role_on_engagement,
        },
    )
    await session.commit()
    await session.refresh(member)
    return TeamMemberRecord.model_validate(member)


async def remove_team_member(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, clerk_user_id: str
) -> None:
    team = await _team(session, engagement_id)
    member = next((m for m in team if m.clerk_user_id == clerk_user_id), None)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    await session.delete(member)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type="engagement_team_member",
        entity_id=f"{engagement_id}:{clerk_user_id}",
        before={"engagement_id": str(engagement_id), "clerk_user_id": clerk_user_id},
    )
    await session.commit()


async def confirm_independence(
    session: AsyncSession, *, user: AuthenticatedUser, engagement_id: uuid.UUID
) -> TeamMemberRecord:
    team = await _team(session, engagement_id)
    member = next((m for m in team if m.clerk_user_id == user.user_id), None)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not on this engagement's team",
        )
    member.independence_confirmed = True
    member.independence_confirmed_at = datetime.now(UTC)
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="update",
        entity_type="engagement_team_member",
        entity_id=f"{engagement_id}:{user.user_id}",
        after={"independence_confirmed": True},
    )
    await session.commit()
    await session.refresh(member)
    return TeamMemberRecord.model_validate(member)
